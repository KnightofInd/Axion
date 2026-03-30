import json
import re

import httpx

from app.core.config import settings
from app.services.calendar_agent_service import CalendarAgentService
from app.services.task_agent_service import TaskAgentService


class DebriefAgentService:
    def __init__(self) -> None:
        self.calendar_service = CalendarAgentService()
        self.task_service = TaskAgentService()

    async def run(self, email: str, event_id: str, notes_text: str | None = None) -> dict:
        event = self.calendar_service.get_event(email=email, event_id=event_id)
        source_text = (notes_text or event.get("description") or event.get("summary") or "").strip()
        if not source_text:
            return {
                "success": True,
                "message": "No notes found for event; no action items created.",
                "action_items": [],
                "tasks_created": 0,
            }

        extracted = await self._extract_action_items(source_text)
        created_tasks = []
        for item in extracted:
            task = self.task_service.create_task(
                email=email,
                title=item,
                description=f"Debrief from event: {event.get('summary')}",
                priority=3,
                source="debrief",
                due_at=None,
            )
            created_tasks.append(task)

        return {
            "success": True,
            "event": event,
            "action_items": extracted,
            "tasks_created": len(created_tasks),
            "task_ids": [task.get("id") for task in created_tasks],
        }

    async def _extract_action_items(self, text: str) -> list[str]:
        if settings.gemini_api_key:
            try:
                return await self._extract_with_gemini(text)
            except Exception:
                pass
        return self._extract_heuristic(text)

    async def _extract_with_gemini(self, text: str) -> list[str]:
        prompt = {
            "instruction": (
                "Extract action items from this meeting debrief. Return JSON with key action_items as an array of strings."
            ),
            "debrief_text": text,
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_flash_model}:generateContent?key={settings.gemini_api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": json.dumps(prompt)}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
        response.raise_for_status()
        raw = response.json()

        text_response = (
            raw.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
            .strip()
        )
        parsed = self._parse_json(text_response)
        items = [str(item).strip() for item in parsed.get("action_items", []) if str(item).strip()]
        return items[:10]

    def _extract_heuristic(self, text: str) -> list[str]:
        candidates = re.split(r"[\n\.]+", text)
        items = []
        for candidate in candidates:
            line = candidate.strip(" -•\t")
            if not line:
                continue
            lowered = line.lower()
            if any(token in lowered for token in ["will", "todo", "follow up", "send", "prepare", "complete", "review"]):
                items.append(line)
        return items[:10]

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
