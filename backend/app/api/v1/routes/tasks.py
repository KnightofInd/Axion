from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.task_agent_service import TaskAgentService

router = APIRouter()
service = TaskAgentService()


class CreateTaskRequest(BaseModel):
    email: str
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)
    source: Literal["gmail", "calendar", "manual", "debrief"] = "manual"
    due_at: str | None = None


class UpdateTaskRequest(BaseModel):
    email: str
    title: str | None = None
    description: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    source: Literal["gmail", "calendar", "manual", "debrief"] | None = None
    status: Literal["pending", "in_progress", "done"] | None = None
    due_at: str | None = None


@router.post("/")
async def create_task(body: CreateTaskRequest) -> dict:
    try:
        task = service.create_task(
            email=body.email,
            title=body.title,
            description=body.description,
            priority=body.priority,
            source=body.source,
            due_at=body.due_at,
        )
        return {"created": True, "task": task}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Create task failed: {exc}") from exc


@router.get("/")
async def list_tasks(email: str) -> dict:
    try:
        return service.list_tasks_scored(email=email)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"List tasks failed: {exc}") from exc


@router.patch("/{task_id}")
async def update_task(task_id: str, body: UpdateTaskRequest) -> dict:
    try:
        task = service.update_task(email=body.email, task_id=task_id, updates=body.model_dump())
        return {"updated": True, "task": task}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Update task failed: {exc}") from exc


@router.delete("/{task_id}")
async def delete_task(task_id: str, email: str) -> dict:
    try:
        return service.delete_task(email=email, task_id=task_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Delete task failed: {exc}") from exc


@router.get("/commitments/overdue")
async def list_overdue_commitments(email: str) -> dict:
    try:
        return service.list_overdue_commitments(email=email)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Overdue commitments failed: {exc}") from exc
