import json
import re
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
            except Exception:
                pass

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
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_flash_model}:generateContent?key={settings.gemini_api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": json.dumps(prompt),
                        }
                    ]
                }
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
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
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(text)
        parsed["mode"] = "gemini"
        parsed.setdefault("tasks", [])
        parsed.setdefault("commitments", [])
        return parsed

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
