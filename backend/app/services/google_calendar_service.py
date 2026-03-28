from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from app.services.google_oauth_service import GoogleOAuthService


class GoogleCalendarService:
    def __init__(self) -> None:
        self.oauth_service = GoogleOAuthService()

    async def get_upcoming_events(self, email: str, limit: int = 5) -> dict:
        try:
            credentials = self.oauth_service.get_valid_credentials(email)
            calendar = build("calendar", "v3", credentials=credentials, cache_discovery=False)

            now = datetime.now(timezone.utc).isoformat()
            response = (
                calendar.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=limit,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            items = response.get("items", [])
            events = [
                {
                    "id": item.get("id"),
                    "summary": item.get("summary"),
                    "start": (item.get("start") or {}).get("dateTime") or (item.get("start") or {}).get("date"),
                    "end": (item.get("end") or {}).get("dateTime") or (item.get("end") or {}).get("date"),
                    "status": item.get("status"),
                    "html_link": item.get("htmlLink"),
                }
                for item in items
            ]

            return {
                "connected": True,
                "message": "Calendar events fetched successfully.",
                "events": events,
                "requested_limit": limit,
                "fetched_count": len(events),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "connected": False,
                "message": f"Failed to fetch Calendar events: {exc}",
                "events": [],
            }

    async def create_test_event(self, email: str) -> dict:
        try:
            credentials = self.oauth_service.get_valid_credentials(email)
            calendar = build("calendar", "v3", credentials=credentials, cache_discovery=False)

            starts_at = datetime.now(timezone.utc) + timedelta(hours=2)
            ends_at = starts_at + timedelta(minutes=30)
            event_payload = {
                "summary": "AXION Test Event",
                "description": "Created by AXION Phase 1 connection test.",
                "start": {"dateTime": starts_at.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": ends_at.isoformat(), "timeZone": "UTC"},
            }
            created = calendar.events().insert(calendarId="primary", body=event_payload).execute()

            return {
                "created": True,
                "message": "Calendar test event created.",
                "event": {
                    "id": created.get("id"),
                    "summary": created.get("summary"),
                    "start": (created.get("start") or {}).get("dateTime"),
                    "end": (created.get("end") or {}).get("dateTime"),
                    "html_link": created.get("htmlLink"),
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "created": False,
                "message": f"Failed to create Calendar test event: {exc}",
            }
