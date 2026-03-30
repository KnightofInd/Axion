from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.debrief_agent_service import DebriefAgentService
from app.services.orchestrator_service import OrchestratorService

router = APIRouter()
orchestrator = OrchestratorService()
debrief_agent = DebriefAgentService()


class DebriefRequest(BaseModel):
    email: str
    event_id: str
    notes_text: str | None = None


@router.post("/run")
async def run_pipeline(email: str, resume: bool = True, max_focus_blocks: int = 2) -> dict:
    try:
        return await orchestrator.run_pipeline(email=email, resume=resume, max_focus_blocks=max_focus_blocks)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Orchestrator run failed: {exc}") from exc


@router.get("/runs/latest")
async def get_latest_run(email: str) -> dict:
    try:
        return orchestrator.get_latest_run(email=email)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Fetch latest run failed: {exc}") from exc


@router.post("/debrief")
async def run_meeting_debrief(body: DebriefRequest) -> dict:
    try:
        return await debrief_agent.run(email=body.email, event_id=body.event_id, notes_text=body.notes_text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Debrief run failed: {exc}") from exc
