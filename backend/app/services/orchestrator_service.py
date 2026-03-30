import asyncio
from datetime import date, datetime, timezone

from app.db.supabase_client import get_supabase_client
from app.services.briefing_service import BriefingService
from app.services.calendar_agent_service import CalendarAgentService
from app.services.email_agent_service import EmailAgentService
from app.services.google_oauth_service import GoogleOAuthService
from app.services.task_agent_service import TaskAgentService


class OrchestratorService:
    def __init__(self) -> None:
        self.oauth_service = GoogleOAuthService()
        self.email_agent = EmailAgentService()
        self.calendar_agent = CalendarAgentService()
        self.task_agent = TaskAgentService()
        self.briefing_service = BriefingService()

    async def run_pipeline(self, email: str, resume: bool = True, max_focus_blocks: int = 2) -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        run = self._get_or_create_run(user_id=user["id"], resume=resume)
        run_id = run["id"]

        try:
            parallel_outputs = await self._run_parallel_base_steps(email=email, run_id=run_id, resume=resume)
            conflicts = self._run_or_resume_step(
                run_id=run_id,
                step_name="conflict_resolver",
                resume=resume,
                action=lambda: self._resolve_conflicts(email=email, free_slots=parallel_outputs["calendar_scan"], max_focus_blocks=max_focus_blocks),
            )
            focus_write = self._run_or_resume_step(
                run_id=run_id,
                step_name="focus_block_write",
                resume=resume,
                action=lambda: self._write_focus_blocks(email=email, matches=conflicts.get("matches", [])),
            )
            commitments = self._run_or_resume_step(
                run_id=run_id,
                step_name="commitment_tracker",
                resume=resume,
                action=lambda: self.task_agent.list_overdue_commitments(email=email),
            )
            scored_tasks = self.task_agent.list_tasks_scored(email=email).get("tasks", [])
            briefing = await self._run_or_resume_async_step(
                run_id=run_id,
                step_name="daily_briefing",
                resume=resume,
                action=lambda: self.briefing_service.generate_daily_briefing(
                    email=email,
                    context={
                        "email_agent": parallel_outputs["email_agent"],
                        "calendar_scan": parallel_outputs["calendar_scan"],
                        "conflicts": conflicts,
                        "scheduled_focus_blocks": focus_write.get("events", []),
                        "overdue_commitments": commitments.get("commitments", []),
                        "scored_tasks": scored_tasks,
                    },
                ),
            )

            summary = {
                "email_agent": parallel_outputs["email_agent"],
                "calendar_scan": parallel_outputs["calendar_scan"],
                "conflicts": conflicts,
                "focus_block_write": focus_write,
                "commitment_tracker": commitments,
                "daily_briefing": briefing,
            }
            self._mark_run_completed(run_id=run_id, summary=summary)

            return {
                "success": True,
                "run_id": run_id,
                "status": "completed",
                "summary": summary,
            }
        except Exception as exc:  # noqa: BLE001
            self._mark_run_failed(run_id=run_id, error=str(exc))
            raise

    def get_latest_run(self, email: str) -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        db = get_supabase_client()
        run_result = (
            db.table("pipeline_runs")
            .select("*")
            .eq("user_id", user.get("id"))
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if not run_result.data:
            return {"exists": False}

        run = run_result.data[0]
        steps_result = (
            db.table("pipeline_steps")
            .select("*")
            .eq("run_id", run.get("id"))
            .order("created_at", desc=False)
            .execute()
        )

        return {
            "exists": True,
            "run": run,
            "steps": steps_result.data or [],
        }

    async def _run_parallel_base_steps(self, email: str, run_id: str, resume: bool) -> dict:
        email_cached = self._get_step_if_completed(run_id, "email_agent") if resume else None
        cal_cached = self._get_step_if_completed(run_id, "calendar_scan") if resume else None

        outputs: dict = {}

        email_task = None
        calendar_task = None

        if email_cached is not None:
            outputs["email_agent"] = email_cached
        else:
            email_task = asyncio.create_task(
                self._run_or_resume_async_step(
                    run_id=run_id,
                    step_name="email_agent",
                    resume=False,
                    action=lambda: self.email_agent.run(email=email, fetch_limit=50, max_for_ai=15),
                )
            )

        if cal_cached is not None:
            outputs["calendar_scan"] = cal_cached
        else:
            calendar_task = asyncio.create_task(
                asyncio.to_thread(
                    self._run_or_resume_step,
                    run_id,
                    "calendar_scan",
                    False,
                    lambda: self.calendar_agent.analyze_free_slots(email=email, days=7, min_minutes=30),
                )
            )

        if email_task:
            outputs["email_agent"] = await email_task
        if calendar_task:
            outputs["calendar_scan"] = await calendar_task

        return outputs

    def _resolve_conflicts(self, email: str, free_slots: dict, max_focus_blocks: int = 2) -> dict:
        tasks = self.task_agent.list_tasks_scored(email=email).get("tasks", [])
        pending = [item for item in tasks if item.get("status") in {"pending", "in_progress"}]
        slots = free_slots.get("free_slots", [])

        match_count = min(len(pending), len(slots), max_focus_blocks)
        matches = []
        for idx in range(match_count):
            task = pending[idx]
            slot = slots[idx]
            score = int(task.get("computed_score", 0))
            duration = 45
            if score >= 140:
                duration = 90
            elif score >= 100:
                duration = 60

            if duration > int(slot.get("duration_minutes", 0)):
                duration = max(30, int(slot.get("duration_minutes", 0)))

            matches.append(
                {
                    "task_id": task.get("id"),
                    "task_title": task.get("title"),
                    "task_score": score,
                    "slot_start": slot.get("start"),
                    "slot_end": slot.get("end"),
                    "duration_minutes": duration,
                }
            )

        return {
            "matches": matches,
            "matched_count": len(matches),
            "pending_tasks_considered": len(pending),
            "free_slots_considered": len(slots),
        }

    def _write_focus_blocks(self, email: str, matches: list[dict]) -> dict:
        events = []
        failures = []

        for match in matches:
            result = self.calendar_agent.create_focus_block_from_slot(
                email=email,
                slot_start_iso=match.get("slot_start"),
                duration_minutes=int(match.get("duration_minutes", 60)),
                title=f"AXION Focus: {match.get('task_title', 'Priority Task')[:60]}",
                description=f"Auto-scheduled from orchestrator for task {match.get('task_id')}",
            )
            if result.get("created"):
                event = result.get("event", {})
                event["task_id"] = match.get("task_id")
                events.append(event)
            else:
                failures.append({"task_id": match.get("task_id"), "error": result.get("message")})

        return {
            "requested": len(matches),
            "created": len(events),
            "failed": len(failures),
            "events": events,
            "failures": failures,
        }

    def _get_or_create_run(self, user_id: str, resume: bool) -> dict:
        db = get_supabase_client()
        today = date.today().isoformat()

        existing = (
            db.table("pipeline_runs")
            .select("*")
            .eq("user_id", user_id)
            .eq("pipeline_date", today)
            .limit(1)
            .execute()
        )

        if existing.data:
            run = existing.data[0]
            if resume and run.get("status") in {"running", "failed", "completed"}:
                return run

            updated = (
                db.table("pipeline_runs")
                .update(
                    {
                        "status": "running",
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "finished_at": None,
                        "last_error": None,
                        "summary": {},
                    }
                )
                .eq("id", run.get("id"))
                .execute()
            )
            return updated.data[0]

        inserted = (
            db.table("pipeline_runs")
            .insert(
                {
                    "user_id": user_id,
                    "pipeline_date": today,
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "summary": {},
                }
            )
            .execute()
        )
        return inserted.data[0]

    def _get_step_if_completed(self, run_id: str, step_name: str) -> dict | None:
        db = get_supabase_client()
        result = (
            db.table("pipeline_steps")
            .select("*")
            .eq("run_id", run_id)
            .eq("step_name", step_name)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None

        step = result.data[0]
        if step.get("status") == "completed":
            return step.get("output", {})
        return None

    def _run_or_resume_step(self, run_id: str, step_name: str, resume: bool, action):
        if resume:
            cached = self._get_step_if_completed(run_id, step_name)
            if cached is not None:
                return cached

        self._mark_step_running(run_id, step_name)
        try:
            output = action()
            self._mark_step_completed(run_id, step_name, output)
            return output
        except Exception as exc:  # noqa: BLE001
            self._mark_step_failed(run_id, step_name, str(exc))
            raise

    async def _run_or_resume_async_step(self, run_id: str, step_name: str, resume: bool, action):
        if resume:
            cached = self._get_step_if_completed(run_id, step_name)
            if cached is not None:
                return cached

        self._mark_step_running(run_id, step_name)
        try:
            output = await action()
            self._mark_step_completed(run_id, step_name, output)
            return output
        except Exception as exc:  # noqa: BLE001
            self._mark_step_failed(run_id, step_name, str(exc))
            raise

    def _mark_step_running(self, run_id: str, step_name: str) -> None:
        db = get_supabase_client()
        db.table("pipeline_steps").upsert(
            {
                "run_id": run_id,
                "step_name": step_name,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
                "error": None,
            },
            on_conflict="run_id,step_name",
        ).execute()

    def _mark_step_completed(self, run_id: str, step_name: str, output: dict) -> None:
        db = get_supabase_client()
        db.table("pipeline_steps").upsert(
            {
                "run_id": run_id,
                "step_name": step_name,
                "status": "completed",
                "output": output,
                "error": None,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="run_id,step_name",
        ).execute()

    def _mark_step_failed(self, run_id: str, step_name: str, error: str) -> None:
        db = get_supabase_client()
        db.table("pipeline_steps").upsert(
            {
                "run_id": run_id,
                "step_name": step_name,
                "status": "failed",
                "error": error,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="run_id,step_name",
        ).execute()

    def _mark_run_completed(self, run_id: str, summary: dict) -> None:
        db = get_supabase_client()
        db.table("pipeline_runs").update(
            {
                "status": "completed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": None,
                "summary": summary,
            }
        ).eq("id", run_id).execute()

    def _mark_run_failed(self, run_id: str, error: str) -> None:
        db = get_supabase_client()
        db.table("pipeline_runs").update(
            {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": error,
            }
        ).eq("id", run_id).execute()
