from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.core.config import settings
from app.db.supabase_client import get_supabase_client


class GoogleOAuthService:
    auth_base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/tasks",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def build_authorization_url(self) -> str:
        query = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "access_type": "offline",
            "include_granted_scopes": "true",
            "scope": " ".join(self.scopes),
            "prompt": "consent",
        }

        return f"{self.auth_base_url}?{urlencode(query)}"

    async def exchange_code(self, code: str) -> dict:
        payload = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(self.token_url, data=payload)
        response.raise_for_status()
        return response.json()

    async def get_userinfo(self, access_token: str) -> dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.userinfo_url, headers=headers)
        response.raise_for_status()
        return response.json()

    def save_user_tokens(self, token_payload: dict, userinfo: dict) -> dict:
        expires_in = int(token_payload.get("expires_in", 3600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        row = {
            "google_user_id": userinfo.get("sub"),
            "email": userinfo.get("email"),
            "full_name": userinfo.get("name"),
            "access_token": token_payload.get("access_token"),
            "refresh_token": token_payload.get("refresh_token"),
            "token_expires_at": expires_at.isoformat(),
        }

        db = get_supabase_client()
        result = db.table("users").upsert(row, on_conflict="email").execute()
        return result.data[0] if result.data else row

    def get_user_by_email(self, email: str) -> dict | None:
        db = get_supabase_client()
        result = db.table("users").select("*").eq("email", email).limit(1).execute()
        if not result.data:
            return None
        return result.data[0]

    def get_valid_credentials(self, email: str) -> Credentials:
        user = self.get_user_by_email(email)
        if not user:
            raise ValueError("User not found. Complete OAuth first.")

        creds = Credentials(
            token=user.get("access_token"),
            refresh_token=user.get("refresh_token"),
            token_uri=self.token_url,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=self.scopes,
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            update_payload = {
                "access_token": creds.token,
                "token_expires_at": creds.expiry.isoformat() if creds.expiry else None,
            }
            db = get_supabase_client()
            db.table("users").update(update_payload).eq("email", email).execute()

        return creds
