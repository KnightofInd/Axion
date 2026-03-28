from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from app.services.google_oauth_service import GoogleOAuthService


class CalendarAgentService:
    def __init__(self) -> None:
        self.oauth_service = GoogleOAuthService()

    def analyze_free_slots(self, email: str, days: int = 7, min_minutes: int = 30) -> dict:
        credentials = self.oauth_service.get_valid_credentials(email)
        calendar = build("calendar", "v3", credentials=credentials, cache_discovery=False)

        start = datetime.now(timezone.utc)
        end = start + timedelta(days=days)
        response = (
            calendar.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=250,
            )
            .execute()
        )
        events = response.get("items", [])
        free_slots = self._compute_free_slots(events, start, end, min_minutes)

        scored_slots = []
        for slot in free_slots:
            slot["score"] = self._score_slot(slot)
            scored_slots.append(slot)

        scored_slots.sort(key=lambda item: item.get("score", 0), reverse=True)
        return {
            "success": True,
            "days": days,
            "min_minutes": min_minutes,
            "events_count": len(events),
            "free_slots_count": len(scored_slots),
            "free_slots": scored_slots,
        }

    def create_focus_block(self, email: str, duration_minutes: int = 60) -> dict:
        analysis = self.analyze_free_slots(email=email, days=7, min_minutes=30)
        if analysis.get("free_slots_count", 0) == 0:
            return {
                "created": False,
                "message": "No free slots above 30 minutes found in next 7 days.",
            }

        best_slot = analysis["free_slots"][0]
        start_iso = best_slot["start"]
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        credentials = self.oauth_service.get_valid_credentials(email)
        calendar = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        payload = {
            "summary": "AXION Focus Block",
            "description": "Auto-scheduled by AXION Calendar Agent",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        }
        created = calendar.events().insert(calendarId="primary", body=payload).execute()

        return {
            "created": True,
            "message": "Focus block created from top-scoring free slot.",
            "slot": best_slot,
            "event": {
                "id": created.get("id"),
                "summary": created.get("summary"),
                "start": (created.get("start") or {}).get("dateTime"),
                "end": (created.get("end") or {}).get("dateTime"),
                "html_link": created.get("htmlLink"),
            },
        }

    def _compute_free_slots(self, events: list[dict], window_start: datetime, window_end: datetime, min_minutes: int) -> list[dict]:
        busy_ranges: list[tuple[datetime, datetime]] = []
        for event in events:
            start_raw = (event.get("start") or {}).get("dateTime")
            end_raw = (event.get("end") or {}).get("dateTime")
            if not start_raw or not end_raw:
                continue
            start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            busy_ranges.append((start_dt, end_dt))

        busy_ranges.sort(key=lambda item: item[0])

        slots: list[dict] = []
        cursor = window_start
        for start_dt, end_dt in busy_ranges:
            if start_dt > cursor:
                gap = start_dt - cursor
                if gap.total_seconds() >= min_minutes * 60:
                    slots.append(
                        {
                            "start": cursor.isoformat(),
                            "end": start_dt.isoformat(),
                            "duration_minutes": int(gap.total_seconds() // 60),
                        }
                    )
            cursor = max(cursor, end_dt)

        if window_end > cursor:
            gap = window_end - cursor
            if gap.total_seconds() >= min_minutes * 60:
                slots.append(
                    {
                        "start": cursor.isoformat(),
                        "end": window_end.isoformat(),
                        "duration_minutes": int(gap.total_seconds() // 60),
                    }
                )

        return slots

    def _score_slot(self, slot: dict) -> int:
        start_dt = datetime.fromisoformat(slot["start"])
        duration_minutes = int(slot.get("duration_minutes", 0))

        hour_bonus = 0
        if 8 <= start_dt.hour <= 11:
            hour_bonus = 25
        elif 12 <= start_dt.hour <= 17:
            hour_bonus = 15
        elif 18 <= start_dt.hour <= 21:
            hour_bonus = 5

        duration_bonus = min(duration_minutes, 180) // 6
        return hour_bonus + duration_bonus
