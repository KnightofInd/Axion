from fastapi import APIRouter

from app.services.google_calendar_service import GoogleCalendarService
from app.services.gmail_service import GmailService

router = APIRouter()
gmail_service = GmailService()
calendar_service = GoogleCalendarService()


@router.get("/gmail/recent")
async def get_recent_emails(email: str, limit: int = 10) -> dict:
    return await gmail_service.get_recent_emails(email=email, limit=limit)


@router.get("/calendar/upcoming")
async def get_upcoming_events(email: str, limit: int = 5) -> dict:
    return await calendar_service.get_upcoming_events(email=email, limit=limit)


@router.post("/calendar/test-event")
async def create_test_event(email: str) -> dict:
    return await calendar_service.create_test_event(email=email)
