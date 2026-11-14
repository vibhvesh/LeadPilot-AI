"""Send one message with the user's Gmail token. Tests replace send_gmail."""

import base64
from email.message import EmailMessage

import httpx

from app.core.config import get_settings


def send_gmail(*, refresh_token: str, to: str, subject: str, body: str, bcc: str) -> str:
    settings = get_settings()
    token = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    token.raise_for_status()
    access = token.json().get("access_token") or ""
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    if bcc:
        message["Bcc"] = bcc
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = httpx.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access}"},
        json={"raw": raw},
        timeout=20,
    )
    sent.raise_for_status()
    return str(sent.json().get("id") or "")
