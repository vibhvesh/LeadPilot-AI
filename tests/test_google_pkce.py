"""Google login must send a real PKCE challenge, and the callback must return the verifier."""

import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from authlib.oauth2.rfc7636 import create_s256_code_challenge

from app.auth.google import reset_google_client
from app.core.config import get_settings

DISCOVERY = {
    "issuer": "https://accounts.google.com",
    "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_endpoint": "https://oauth2.googleapis.com/token",
    "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
    "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
}


@pytest.fixture
def google_ready(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8000")
    monkeypatch.setattr("app.auth.google.RETRY_DELAY_SECONDS", 0)
    get_settings.cache_clear()
    reset_google_client()
    yield
    reset_google_client()
    get_settings.cache_clear()


def _install_metadata(monkeypatch, behavior):
    async def load_server_metadata(self):
        await behavior(self)
        return self.server_metadata

    monkeypatch.setattr(
        "authlib.integrations.base_client.async_app.AsyncOAuth2Mixin.load_server_metadata",
        load_server_metadata,
    )


async def _successful_metadata(self):
    self.server_metadata.update(DISCOVERY)
    self.server_metadata["_loaded_at"] = time.time()


def test_authorize_redirect_includes_s256_challenge_and_callback_sends_verifier(client, google_ready, monkeypatch):
    _install_metadata(monkeypatch, lambda self: _successful_metadata(self))
    response = client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    query = parse_qs(urlparse(location).query)
    assert query["code_challenge_method"] == ["S256"]
    challenge = query["code_challenge"][0]
    assert challenge
    state = query["state"][0]

    captured = {}

    async def fetch_access_token(self, redirect_uri=None, **kwargs):
        captured["redirect_uri"] = redirect_uri
        captured["kwargs"] = kwargs
        return {"access_token": "token", "token_type": "Bearer"}

    async def userinfo(self, **kwargs):
        return {"email": "new.google.user@example.com", "email_verified": True, "name": "New User", "sub": "google-sub"}

    monkeypatch.setattr(
        "authlib.integrations.base_client.async_app.AsyncOAuth2Mixin.fetch_access_token",
        fetch_access_token,
    )
    monkeypatch.setattr(
        "authlib.integrations.base_client.async_openid.AsyncOpenIDMixin.userinfo",
        userinfo,
    )

    callback = client.get(
        "/auth/google/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 200
    verifier = captured["kwargs"]["code_verifier"]
    assert create_s256_code_challenge(verifier) == challenge
    assert captured["kwargs"]["code"] == "auth-code"
    assert captured["redirect_uri"] == "http://localhost:8000/auth/google/callback"


def test_discovery_timeout_is_retried_then_returns_a_friendly_page(client, google_ready, monkeypatch):
    attempts = {"count": 0}

    async def flaky(self):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.ConnectTimeout("timed out")
        await _successful_metadata(self)

    _install_metadata(monkeypatch, flaky)
    response = client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 302
    assert attempts["count"] == 3
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0]


def test_token_exchange_timeout_is_not_retried_and_returns_503(client, google_ready, monkeypatch):
    _install_metadata(monkeypatch, lambda self: _successful_metadata(self))
    start = client.get("/auth/google/login", follow_redirects=False)
    query = parse_qs(urlparse(start.headers["location"]).query)
    calls = {"count": 0}

    async def fetch_access_token(self, redirect_uri=None, **kwargs):
        calls["count"] += 1
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(
        "authlib.integrations.base_client.async_app.AsyncOAuth2Mixin.fetch_access_token",
        fetch_access_token,
    )
    callback = client.get(
        "/auth/google/callback",
        params={"code": "auth-code", "state": query["state"][0]},
        follow_redirects=False,
    )
    assert calls["count"] == 1
    assert callback.status_code == 503
    assert "try again" in callback.text.lower()
    assert "Google sign-in failed" not in callback.text


def test_callback_metadata_failure_is_retried(client, google_ready, monkeypatch):
    _install_metadata(monkeypatch, lambda self: _successful_metadata(self))
    start = client.get("/auth/google/login", follow_redirects=False)
    query = parse_qs(urlparse(start.headers["location"]).query)
    attempts = {"count": 0}

    async def flaky(self):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.ConnectTimeout("timed out")
        await _successful_metadata(self)

    _install_metadata(monkeypatch, flaky)

    async def fetch_access_token(self, redirect_uri=None, **kwargs):
        return {"access_token": "token", "token_type": "Bearer"}

    async def userinfo(self, **kwargs):
        return {"email": "retry.user@example.com", "email_verified": True, "name": "Retry User", "sub": "retry-sub"}

    monkeypatch.setattr(
        "authlib.integrations.base_client.async_app.AsyncOAuth2Mixin.fetch_access_token",
        fetch_access_token,
    )
    monkeypatch.setattr(
        "authlib.integrations.base_client.async_openid.AsyncOpenIDMixin.userinfo",
        userinfo,
    )
    callback = client.get(
        "/auth/google/callback",
        params={"code": "auth-code", "state": query["state"][0]},
        follow_redirects=False,
    )
    assert attempts["count"] >= 3
    assert callback.status_code == 200


def test_discovery_failure_does_not_return_500(client, google_ready, monkeypatch):
    async def always_down(self):
        raise httpx.ConnectTimeout("timed out")

    _install_metadata(monkeypatch, always_down)
    response = client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 503
    assert "try again" in response.text.lower()
    assert "Traceback" not in response.text
