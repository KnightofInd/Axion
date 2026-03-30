import json
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.db.supabase_client import get_supabase_client
from app.services.briefing_service import BriefingService
from app.services.google_oauth_service import GoogleOAuthService
from app.services.orchestrator_service import OrchestratorService
from app.services.task_agent_service import TaskAgentService


class SidebarService:
    def __init__(self) -> None:
        self.oauth_service = GoogleOAuthService()
        self.task_service = TaskAgentService()
        self.briefing_service = BriefingService()
        self.orchestrator = OrchestratorService()

    async def get_overview(self, email: str, commitments_tab: str = "i_owe") -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        user_id = user.get("id")
        db = get_supabase_client()

        tasks_payload = self.task_service.list_tasks_scored(email=email)
        tasks = tasks_payload.get("tasks", [])
        priority_tasks = [item for item in tasks if item.get("status") in {"pending", "in_progress"}][:3]

        latest_run = self.orchestrator.get_latest_run(email=email)
        run_summary = (latest_run.get("run") or {}).get("summary") if latest_run.get("exists") else None

        briefing = await self._resolve_briefing(email=email, run_summary=run_summary)
        commitments = self._get_commitments(email=email)

        i_owe = [item for item in commitments if item.get("direction") == "given"]
        they_owe = [item for item in commitments if item.get("direction") == "received"]
        selected = i_owe if commitments_tab == "i_owe" else they_owe

        focus_blocks = (((run_summary or {}).get("focus_block_write") or {}).get("events") or [])
        next_free_slot = self._extract_next_free_slot(run_summary)

        stats = {
            "tasks": len(priority_tasks),
            "focus_blocks": len(focus_blocks),
            "commitments": len(commitments),
        }

        return {
            "status": "synced",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "briefing": briefing,
            "stats": stats,
            "priority_tasks": priority_tasks,
            "calendar": {
                "focus_blocks": focus_blocks,
                "next_free_slot": next_free_slot,
            },
            "commitments": {
                "i_owe": i_owe,
                "they_owe": they_owe,
                "selected_tab": commitments_tab,
                "selected_items": selected,
            },
            "empty": len(priority_tasks) == 0 and len(commitments) == 0,
            "latest_run": latest_run.get("run") if latest_run.get("exists") else None,
            "user": {
                "id": user_id,
                "email": user.get("email"),
                "name": user.get("full_name"),
            },
        }

    async def sync(self, email: str, resume: bool = True) -> dict:
        result = await self.orchestrator.run_pipeline(email=email, resume=resume, max_focus_blocks=2)
        overview = await self.get_overview(email=email, commitments_tab="i_owe")
        return {
            "synced": True,
            "pipeline": {
                "run_id": result.get("run_id"),
                "status": result.get("status"),
            },
            "overview": overview,
        }

    async def ask(self, email: str, question: str) -> dict:
        question_clean = (question or "").strip()
        if not question_clean:
            return {
                "answer": "Ask me anything about your tasks, calendar, or commitments.",
                "mode": "heuristic",
            }

        context = await self.get_overview(email=email, commitments_tab="i_owe")
        if settings.gemini_api_key:
            try:
                answer = await self._ask_with_gemini(question_clean, context)
                return {
                    "answer": answer,
                    "mode": "gemini",
                }
            except Exception as exc:  # noqa: BLE001
                heuristic = self._ask_heuristic(question_clean, context)
                heuristic["fallback_reason"] = str(exc)
                return heuristic

        return self._ask_heuristic(question_clean, context)

    async def _resolve_briefing(self, email: str, run_summary: dict | None) -> dict:
        db = get_supabase_client()
        user = self.oauth_service.get_user_by_email(email)
        briefing_result = (
            db.table("briefings")
            .select("*")
            .eq("user_id", user.get("id"))
            .order("briefing_date", desc=True)
            .limit(1)
            .execute()
        )

        if briefing_result.data:
            row = briefing_result.data[0]
            payload = row.get("payload", {})
            return {
                "text": payload.get("summary") or "Briefing is ready.",
                "payload": payload,
                "briefing_date": row.get("briefing_date"),
                "generated_by": row.get("generated_by"),
            }

        briefing_context = run_summary or {
            "scored_tasks": self.task_service.list_tasks_scored(email=email).get("tasks", []),
            "overdue_commitments": self.task_service.list_overdue_commitments(email=email).get("commitments", []),
            "scheduled_focus_blocks": [],
        }
        generated = await self.briefing_service.generate_daily_briefing(email=email, context=briefing_context)
        payload = generated.get("payload", {})
        return {
            "text": payload.get("summary") or "Briefing generated.",
            "payload": payload,
            "briefing_date": generated.get("briefing_date"),
            "generated_by": generated.get("stored", {}).get("generated_by"),
        }

    def _get_commitments(self, email: str) -> list[dict]:
        user = self.oauth_service.get_user_by_email(email)
        db = get_supabase_client()
        result = (
            db.table("commitments")
            .select("*")
            .eq("user_id", user.get("id"))
            .order("due_at", desc=False)
            .limit(10)
            .execute()
        )
        return result.data or []

    def _extract_next_free_slot(self, run_summary: dict | None) -> str | None:
        free_slots = (((run_summary or {}).get("calendar_scan") or {}).get("free_slots") or [])
        if not free_slots:
            return None
        return free_slots[0].get("start")

    async def _ask_with_gemini(self, question: str, context: dict) -> str:
        prompt = {
            "instruction": "Answer the user question from AXION context in 2-3 concise sentences.",
            "question": question,
            "context": context,
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_pro_model}:generateContent?key={settings.gemini_api_key}"
        )
        request_payload = {
            "contents": [{"parts": [{"text": json.dumps(prompt)}]}],
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=request_payload)
        response.raise_for_status()

        raw = response.json()
        return (
            raw.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "AXION has no answer right now.")
            .strip()
        )

    def _ask_heuristic(self, question: str, context: dict) -> dict:
        lowered = question.lower()
        commitments = context.get("commitments", {}).get("they_owe", [])
        tasks = context.get("priority_tasks", [])

        if "promise" in lowered or "owe" in lowered:
            if not commitments:
                return {"answer": "No tracked promises found this week.", "mode": "heuristic"}
            top = commitments[:3]
            lines = [item.get("text", "Commitment")[:120] for item in top]
            return {"answer": "You have these tracked commitments: " + " | ".join(lines), "mode": "heuristic"}

        if "task" in lowered or "priority" in lowered:
            if not tasks:
                return {"answer": "No priority tasks are currently pending.", "mode": "heuristic"}
            lines = [f"{item.get('title')} (P{item.get('priority')})" for item in tasks[:3]]
            return {"answer": "Top tasks: " + ", ".join(lines), "mode": "heuristic"}

        return {
            "answer": "AXION is synced. Ask about promises, tasks, focus blocks, or commitments.",
            "mode": "heuristic",
        }
