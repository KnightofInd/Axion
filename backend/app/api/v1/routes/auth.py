from fastapi import APIRouter, HTTPException

from app.services.google_oauth_service import GoogleOAuthService

router = APIRouter()
service = GoogleOAuthService()


@router.get("/google/url")
async def get_google_oauth_url() -> dict[str, str]:
    return {"authorization_url": service.build_authorization_url()}


@router.get("/google/callback")
async def google_oauth_callback(code: str) -> dict:
    try:
        token_payload = await service.exchange_code(code)
        userinfo = await service.get_userinfo(token_payload["access_token"])
        user = service.save_user_tokens(token_payload, userinfo)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {exc}") from exc

    return {
        "connected": True,
        "message": "Google OAuth completed and tokens stored.",
        "email": user.get("email"),
    }
