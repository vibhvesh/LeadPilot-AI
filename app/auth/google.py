"""Google OpenID Connect client.

PKCE is enabled on the OAuth client itself. Authlib only creates a
code_verifier and code_challenge when ``code_challenge_method`` is part of
``client_kwargs``. Passing that value to ``authorize_redirect`` only copies
it onto the query string and leaves the challenge out, which Google rejects.
"""

import asyncio
import logging

import httpx
from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings

log = logging.getLogger(__name__)

DISCOVERY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 0.4
DISCOVERY_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

_oauth = OAuth()


class GoogleUnavailable(Exception):
    """Google's discovery or token endpoint could not be reached."""


def google_client():
    settings = get_settings()
    if not settings.google_enabled:
        return None
    if "google" not in _oauth._clients:
        _oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url=settings.google_discovery_url,
            client_kwargs={
                "scope": "openid email profile",
                "code_challenge_method": "S256",
                "timeout": DISCOVERY_TIMEOUT,
            },
        )
    return _oauth.google


def reset_google_client() -> None:
    _oauth._clients.pop("google", None)
    _oauth._registry.pop("google", None)


async def begin_google_login(request):
    client = google_client()
    settings = get_settings()
    return await _call_with_retry(lambda: client.authorize_redirect(request, settings.redirect_uri()))


async def complete_google_login(request):
    client = google_client()
    return await _call_with_retry(lambda: client.authorize_access_token(request))


async def _call_with_retry(operation):
    last_error = None
    for attempt in range(1, DISCOVERY_ATTEMPTS + 1):
        try:
            return await operation()
        except httpx.HTTPError as exc:
            last_error = exc
            log.warning(
                "Google request failed (%s) attempt %s/%s",
                exc.__class__.__name__,
                attempt,
                DISCOVERY_ATTEMPTS,
            )
            if attempt < DISCOVERY_ATTEMPTS and RETRY_DELAY_SECONDS:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)
    log.error("Google sign-in failed after %s attempts", DISCOVERY_ATTEMPTS, exc_info=last_error)
    raise GoogleUnavailable("Google sign-in is temporarily unavailable") from last_error
