"""Tell an external Grok Bot that a deep-search request is waiting."""

import httpx

from app.core.config import get_settings

SECRET_HEADER = "X-LeadPilot-Webhook-Secret"


def dispatch(payload: dict) -> tuple[str, str]:
    settings = get_settings()
    url = (settings.grokbot_webhook_url or "").strip()
    if not url:
        return "not_configured", ""
    headers = {"Content-Type": "application/json", "User-Agent": "LeadPilot/1.0"}
    if settings.grokbot_webhook_secret:
        headers[SECRET_HEADER] = settings.grokbot_webhook_secret
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return "failed", exc.__class__.__name__
    return "sent", ""
