import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.core.config import settings
from app.db.supabase_client import get_supabase_client
from app.services.gmail_service import GmailService
from app.services.google_oauth_service import GoogleOAuthService

ACTION_KEYWORDS = [
    "action required",
    "please",
    "deadline",
    "follow up",
    "schedule",
    "meeting",
    "submit",
    "review",
    "send",
    "complete",
    "due",
    "asap",
    "today",
    "tomorrow",
]

COMMITMENT_HINTS = ["i will", "we will", "promised", "commit", "by ", "before "]


class GeminiFallbackError(RuntimeError):
    def __init__(self, attempts: list[dict]):
        super().__init__("All Gemini fallback models failed.")
        self.attempts = attempts


class EmailAgentService:
    def __init__(self) -> None:
        self.gmail_service = GmailService()
        self.oauth_service = GoogleOAuthService()

    async def run(self, email: str, fetch_limit: int = 50, max_for_ai: int = 15) -> dict:
        fetched = await self.gmail_service.get_recent_emails(email=email, limit=fetch_limit)
        if not fetched.get("connected"):
            return {
                "success": False,
                "message": fetched.get("message", "Failed to fetch Gmail emails."),
                "tasks_saved": 0,
                "commitments_saved": 0,
            }

        emails = fetched.get("emails", [])
        filtered = self._filter_actionable(emails)
        selected = filtered[:max_for_ai]

        extracted = await self._extract_structured(selected)
        saved = self._save_results(email=email, extracted=extracted)

        return {
            "success": True,
            "fetched_count": len(emails),
            "filtered_count": len(filtered),
            "sent_to_ai_count": len(selected),
            "tasks_saved": saved["tasks_saved"],
            "commitments_saved": saved["commitments_saved"],
            "mode": extracted.get("mode", "heuristic"),
            "model_used": extracted.get("model_used"),
            "model_attempts": extracted.get("model_attempts", []),
            "fallback_reason": extracted.get("fallback_reason"),
        }

    def _filter_actionable(self, emails: list[dict]) -> list[dict]:
        filtered: list[dict] = []
        for item in emails:
            content = f"{item.get('subject', '')} {item.get('snippet', '')}".lower()
            if any(keyword in content for keyword in ACTION_KEYWORDS):
                filtered.append(item)
        return filtered

    async def _extract_structured(self, emails: list[dict]) -> dict:
        if not emails:
            return {"mode": "none", "tasks": [], "commitments": []}

        if settings.gemini_api_key:
            try:
                return await self._extract_with_gemini(emails)
            except GeminiFallbackError as exc:
                heuristic = self._extract_heuristic(emails)
                heuristic["model_attempts"] = exc.attempts
                heuristic["fallback_reason"] = f"Gemini extraction failed: {exc.attempts}"
                return heuristic
            except Exception as exc:  # noqa: BLE001
                heuristic = self._extract_heuristic(emails)
                heuristic["fallback_reason"] = f"Gemini extraction failed: {exc}"
                return heuristic

        return self._extract_heuristic(emails)

    async def _extract_with_gemini(self, emails: list[dict]) -> dict:
        prompt = {
            "instruction": (
                "Extract tasks and commitments from these emails. "
                "Return STRICT JSON only with keys: tasks, commitments. "
                "task keys: title, description, due_at_iso, source_message_id, priority(1-5). "
                "commitment keys: text, direction(given|received), due_at_iso, source_message_id."
            ),
            "emails": emails,
        }
        models = self._build_model_fallback_chain()
        attempts: list[dict] = []
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": json.dumps(prompt),
                        }
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in models:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model}:generateContent?key={settings.gemini_api_key}"
                )
                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    raw = response.json()

                    text = (
                        raw.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "{}")
                        .strip()
                    )
                    parsed = self._parse_gemini_json(text)
                    parsed["mode"] = "gemini"
                    parsed["model_used"] = model
                    parsed["model_attempts"] = attempts + [{"model": model, "status": "ok"}]
                    parsed.setdefault("tasks", [])
                    parsed.setdefault("commitments", [])
                    return parsed
                except Exception as exc:  # noqa: BLE001
                    attempts.append({"model": model, "status": "failed", "error": str(exc)})

        raise GeminiFallbackError(attempts)

    def _build_model_fallback_chain(self) -> list[str]:
        models: list[str] = []

        if settings.gemini_flash_model:
            models.append(settings.gemini_flash_model)
        if settings.gemini_pro_model:
            models.append(settings.gemini_pro_model)

        configured = [m.strip() for m in settings.gemini_fallback_models.split(",") if m.strip()]
        models.extend(configured)

        # Reasonable defaults if user hasn't configured fallback models.
        models.extend(["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-lite"])

        deduped: list[str] = []
        for model in models:
            if model not in deduped:
                deduped.append(model)
        return deduped

    def _parse_gemini_json(self, text: str) -> dict:
        cleaned = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise

    def _extract_heuristic(self, emails: list[dict]) -> dict:
        tasks: list[dict] = []
        commitments: list[dict] = []

        for mail in emails:
            subject = (mail.get("subject") or "").strip()
            snippet = (mail.get("snippet") or "").strip()
            source_message_id = mail.get("id")
            due_at = self._extract_due_datetime(mail.get("date"), snippet)

            tasks.append(
                {
                    "title": subject[:180] or "Follow up email",
                    "description": snippet[:1000],
                    "due_at_iso": due_at,
                    "source_message_id": source_message_id,
                    "priority": self._infer_priority(subject, snippet),
                }
            )

            text_blob = f"{subject} {snippet}".lower()
            if any(hint in text_blob for hint in COMMITMENT_HINTS):
                commitments.append(
                    {
                        "text": snippet[:1000] or subject,
                        "direction": "received",
                        "due_at_iso": due_at,
                        "source_message_id": source_message_id,
                    }
                )

        return {"mode": "heuristic", "tasks": tasks, "commitments": commitments}

    def _extract_due_datetime(self, email_date: str | None, snippet: str) -> str | None:
        lowered = (snippet or "").lower()
        base = datetime.now(timezone.utc)
        if "today" in lowered:
            return base.isoformat()
        if "tomorrow" in lowered:
            return (base.replace(hour=17, minute=0, second=0, microsecond=0)).isoformat()

        if email_date:
            try:
                parsed = parsedate_to_datetime(email_date)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.isoformat()
            except Exception:
                return None
        return None

    def _infer_priority(self, subject: str, snippet: str) -> int:
        text = f"{subject} {snippet}".lower()
        if any(k in text for k in ["urgent", "asap", "immediately", "today"]):
            return 5
        if any(k in text for k in ["tomorrow", "deadline", "action required"]):
            return 4
        if "review" in text or "follow up" in text:
            return 3
        return 2

    def _save_results(self, email: str, extracted: dict) -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        user_id = user.get("id")
        db = get_supabase_client()
        tasks_saved = 0
        commitments_saved = 0

        for task in extracted.get("tasks", []):
            payload = {
                "user_id": user_id,
                "source": "gmail",
                "title": task.get("title") or "Untitled task",
                "description": task.get("description"),
                "priority": int(task.get("priority", 3)),
                "due_at": task.get("due_at_iso"),
                "metadata": {
                    "source_message_id": task.get("source_message_id"),
                    "extraction_mode": extracted.get("mode", "heuristic"),
                },
            }
            db.table("tasks").insert(payload).execute()
            tasks_saved += 1

        for commitment in extracted.get("commitments", []):
            payload = {
                "user_id": user_id,
                "direction": commitment.get("direction", "received"),
                "text": commitment.get("text") or "Commitment captured from email",
                "due_at": commitment.get("due_at_iso"),
                "source_message_id": commitment.get("source_message_id"),
                "metadata": {
                    "extraction_mode": extracted.get("mode", "heuristic"),
                },
            }
            db.table("commitments").insert(payload).execute()
            commitments_saved += 1

        return {"tasks_saved": tasks_saved, "commitments_saved": commitments_saved}
