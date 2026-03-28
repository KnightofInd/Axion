from fastapi import APIRouter, HTTPException

from app.services.calendar_agent_service import CalendarAgentService
from app.services.email_agent_service import EmailAgentService

router = APIRouter()
email_agent = EmailAgentService()
calendar_agent = CalendarAgentService()


@router.post("/email/run")
async def run_email_agent(email: str) -> dict:
    try:
        return await email_agent.run(email=email, fetch_limit=50, max_for_ai=15)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Email agent failed: {exc}") from exc


@router.get("/calendar/free-slots")
async def run_calendar_free_slot_scan(email: str) -> dict:
    try:
        return calendar_agent.analyze_free_slots(email=email, days=7, min_minutes=30)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Calendar agent failed: {exc}") from exc


@router.post("/calendar/focus-block")
async def run_calendar_focus_block(email: str, duration_minutes: int = 60) -> dict:
    try:
        return calendar_agent.create_focus_block(email=email, duration_minutes=duration_minutes)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Focus block creation failed: {exc}") from exc
