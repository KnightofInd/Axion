from googleapiclient.discovery import build

from app.services.google_oauth_service import GoogleOAuthService


class GmailService:
    def __init__(self) -> None:
        self.oauth_service = GoogleOAuthService()

    async def get_recent_emails(self, email: str, limit: int = 10) -> dict:
        try:
            credentials = self.oauth_service.get_valid_credentials(email)
            gmail = build("gmail", "v1", credentials=credentials, cache_discovery=False)

            list_response = gmail.users().messages().list(userId="me", maxResults=limit).execute()
            message_refs = list_response.get("messages", [])

            emails: list[dict] = []
            for ref in message_refs:
                raw_message = (
                    gmail.users()
                    .messages()
                    .get(userId="me", id=ref["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
                    .execute()
                )
                headers = {h["name"]: h["value"] for h in raw_message.get("payload", {}).get("headers", [])}
                emails.append(
                    {
                        "id": raw_message.get("id"),
                        "thread_id": raw_message.get("threadId"),
                        "from": headers.get("From"),
                        "subject": headers.get("Subject"),
                        "date": headers.get("Date"),
                        "snippet": raw_message.get("snippet"),
                    }
                )

            return {
                "connected": True,
                "message": "Gmail emails fetched successfully.",
                "emails": emails,
                "requested_limit": limit,
                "fetched_count": len(emails),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "connected": False,
                "message": f"Failed to fetch Gmail emails: {exc}",
                "emails": [],
            }
