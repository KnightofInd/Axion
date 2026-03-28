from datetime import datetime, timedelta, timezone


class TokenManager:
    """Phase 1 token helper: stores token metadata and decides refresh windows."""

    @staticmethod
    def expires_soon(expires_at_iso: str, threshold_minutes: int = 5) -> bool:
        expires_at = datetime.fromisoformat(expires_at_iso)
        now = datetime.now(timezone.utc)
        return expires_at <= (now + timedelta(minutes=threshold_minutes))
