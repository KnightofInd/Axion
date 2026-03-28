from datetime import datetime, timedelta, timezone

from app.db.supabase_client import get_supabase_client
from app.services.google_oauth_service import GoogleOAuthService

SOURCE_WEIGHT = {
    "manual": 1,
    "gmail": 2,
    "calendar": 3,
    "debrief": 2,
}


class TaskAgentService:
    def __init__(self) -> None:
        self.oauth_service = GoogleOAuthService()

    def create_task(
        self,
        email: str,
        title: str,
        description: str | None,
        priority: int,
        source: str,
        due_at: str | None,
    ) -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        payload = {
            "user_id": user.get("id"),
            "title": title,
            "description": description,
            "priority": priority,
            "source": source,
            "due_at": due_at,
            "status": "pending",
            "metadata": {},
        }
        db = get_supabase_client()
        result = db.table("tasks").insert(payload).execute()
        return result.data[0]

    def list_tasks_scored(self, email: str) -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        db = get_supabase_client()
        result = db.table("tasks").select("*").eq("user_id", user.get("id")).execute()
        tasks = result.data or []

        for task in tasks:
            task["computed_score"] = self.compute_task_score(task)

        tasks.sort(key=lambda item: item.get("computed_score", 0), reverse=True)
        return {"count": len(tasks), "tasks": tasks}

    def update_task(self, email: str, task_id: str, updates: dict) -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        allowed = {"title", "description", "priority", "source", "due_at", "status"}
        payload = {k: v for k, v in updates.items() if k in allowed and v is not None}

        db = get_supabase_client()
        result = (
            db.table("tasks")
            .update(payload)
            .eq("id", task_id)
            .eq("user_id", user.get("id"))
            .execute()
        )
        return (result.data or [{}])[0]

    def delete_task(self, email: str, task_id: str) -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        db = get_supabase_client()
        result = db.table("tasks").delete().eq("id", task_id).eq("user_id", user.get("id")).execute()
        deleted = len(result.data or [])
        return {"deleted": deleted > 0, "task_id": task_id}

    def list_overdue_commitments(self, email: str) -> dict:
        user = self.oauth_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        now_iso = datetime.now(timezone.utc).isoformat()
        db = get_supabase_client()
        result = (
            db.table("commitments")
            .select("*")
            .eq("user_id", user.get("id"))
            .in_("status", ["open", "overdue"])
            .lt("due_at", now_iso)
            .execute()
        )
        overdue_items = result.data or []

        if not overdue_items:
            return {"count": 0, "commitments": []}

        ids = [item.get("id") for item in overdue_items if item.get("id")]
        db.table("commitments").update({"status": "overdue"}).in_("id", ids).execute()
        refreshed = db.table("commitments").select("*").in_("id", ids).execute()
        return {"count": len(refreshed.data or []), "commitments": refreshed.data or []}

    def compute_task_score(self, task: dict) -> int:
        base_priority = int(task.get("priority", 3))
        source_weight = SOURCE_WEIGHT.get(task.get("source", "manual"), 1)
        deadline_score = self.deadline_proximity_score(task.get("due_at"))
        return (base_priority * 20) + (source_weight * 10) + deadline_score

    def deadline_proximity_score(self, due_at: str | None) -> int:
        if not due_at:
            return 5

        try:
            due = datetime.fromisoformat(due_at)
            now = datetime.now(timezone.utc)
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            delta = due - now
            if delta <= timedelta(hours=24):
                return 30
            if delta <= timedelta(days=3):
                return 20
            if delta <= timedelta(days=7):
                return 10
            return 5
        except Exception:
            return 5
