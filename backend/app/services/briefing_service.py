import json
from datetime import date

import httpx

from app.core.config import settings
from app.db.supabase_client import get_supabase_client
from app.services.google_oauth_service import GoogleOAuthService


class BriefingService:
    def __init__(self) -> None:
        self.oauth_service = GoogleOAuthService()

    async def generate_daily_briefing(self, email: str, context: dict) -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        briefing_date = date.today().isoformat()
        payload = await self._build_payload(context)

        db = get_supabase_client()
        upsert_payload = {
            "user_id": user.get("id"),
            "briefing_date": briefing_date,
            "payload": payload,
            "generated_by": settings.gemini_pro_model if payload.get("mode") == "gemini" else "heuristic",
        }
        result = db.table("briefings").upsert(upsert_payload, on_conflict="user_id,briefing_date").execute()
        stored = result.data[0] if result.data else upsert_payload

        return {
            "briefing_date": briefing_date,
            "payload": payload,
            "stored": stored,
        }

    async def _build_payload(self, context: dict) -> dict:
        if settings.gemini_api_key:
            try:
                return await self._build_payload_with_gemini(context)
            except Exception as exc:  # noqa: BLE001
                heuristic = self._build_payload_heuristic(context)
                heuristic["fallback_reason"] = str(exc)
                return heuristic

        return self._build_payload_heuristic(context)

    async def _build_payload_with_gemini(self, context: dict) -> dict:
        prompt = {
            "instruction": (
                "Create a concise daily briefing JSON with keys: summary, top_tasks, calendar_plan, "
                "overdue_commitments, suggestions. Keep each field brief and actionable."
            ),
            "context": context,
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_pro_model}:generateContent?key={settings.gemini_api_key}"
        )
        request_payload = {
            "contents": [{"parts": [{"text": json.dumps(prompt)}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=request_payload)
        response.raise_for_status()

        raw = response.json()
        text = (
            raw.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
            .strip()
        )
        parsed = self._parse_json(text)
        parsed["mode"] = "gemini"
        parsed["model_used"] = settings.gemini_pro_model
        return parsed

    def _build_payload_heuristic(self, context: dict) -> dict:
        top_tasks = context.get("scored_tasks", [])[:5]
        overdue = context.get("overdue_commitments", [])
        scheduled = context.get("scheduled_focus_blocks", [])

        summary = (
            f"{len(top_tasks)} priority tasks, {len(overdue)} overdue commitments, "
            f"{len(scheduled)} focus blocks scheduled."
        )

        return {
            "mode": "heuristic",
            "summary": summary,
            "top_tasks": [
                {
                    "title": item.get("title"),
                    "priority": item.get("priority"),
                    "computed_score": item.get("computed_score"),
                }
                for item in top_tasks
            ],
            "calendar_plan": {
                "focus_blocks": [
                    {
                        "title": item.get("summary"),
                        "start": item.get("start"),
                        "end": item.get("end"),
                    }
                    for item in scheduled
                ]
            },
            "overdue_commitments": [
                {
                    "text": item.get("text"),
                    "due_at": item.get("due_at"),
                    "status": item.get("status"),
                }
                for item in overdue
            ],
            "suggestions": [
                "Start with the top-scoring task in the next focus block.",
                "Resolve at least one overdue commitment before end of day.",
            ],
        }

    def _parse_json(self, text: str) -> dict:
        cleaned = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise
