"""Pluggable chat providers. A missing key or a failed call is reported, not replaced with sample text."""

import json
import re

import httpx
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import LLMConfig
from app.providers.access import consume
from app.providers.secrets import resolve_secret

DEFAULT_MODELS = {
    "xai": "grok-3",
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
}
NO_LLM_PROVIDER = "No LLM provider configured"


class LLMClient:
    """Each completion charges one quota unit on the provider that actually answered."""

    def __init__(self, db: Session, user):
        self.db = db
        self.user = user
        self.provider, self.model, self.fallback_note = select_provider(db)
        self.config = db.get(LLMConfig, 1)

    def complete_json(self, *, purpose: str, system: str, prompt: str) -> dict:
        if not self.provider:
            raise AppError(self.fallback_note or NO_LLM_PROVIDER)
        try:
            text = self._call(system, prompt)
            data = parse_json_object(text)
        except AppError:
            raise
        except Exception as exc:
            record(
                self.db,
                user=self.user,
                action="api_call",
                module="ai",
                target=self.provider,
                success=False,
                detail={"purpose": purpose, "error": exc.__class__.__name__},
                note=str(exc)[:300],
            )
            raise AppError(f"{self.provider} request failed ({exc.__class__.__name__})") from exc
        self._charge(self.provider)
        record(
            self.db,
            user=self.user,
            action="api_call",
            module="ai",
            target=self.provider,
            detail={"purpose": purpose, "provider": self.provider, "model": self.model},
        )
        return {"data": data, "provider": self.provider, "model": self.model, "note": ""}

    def _charge(self, provider: str) -> None:
        consume(self.db, self.user, provider, 1)

    def _call(self, system: str, prompt: str) -> str:
        settings = get_settings()
        temperature = self.config.temperature if self.config else 0.2
        max_tokens = self.config.max_tokens if self.config else 800
        if self.provider == "gemini":
            key = resolve_secret(self.db, "gemini", settings.gemini_api_key)
            return _gemini(key, self.model, system, prompt, temperature, max_tokens)
        if self.provider == "openai":
            key = resolve_secret(self.db, "openai", settings.openai_api_key)
            return _openai_compatible("https://api.openai.com/v1/chat/completions", key, self.model, system, prompt, temperature, max_tokens)
        key = resolve_secret(self.db, "xai", settings.xai_api_key)
        return _openai_compatible("https://api.x.ai/v1/chat/completions", key, self.model, system, prompt, temperature, max_tokens)


def select_provider(db: Session) -> tuple[str, str, str]:
    settings = get_settings()
    config = db.get(LLMConfig, 1)
    primary = (config.primary_provider if config else "auto") or "auto"
    requested_model = (config.primary_model if config else "") or ""
    if primary == "auto":
        for name in ("xai", "gemini", "openai"):
            if _has_key(db, settings, name):
                return name, requested_model or _default_model(settings, name), ""
        return "", "", NO_LLM_PROVIDER
    if primary in {"xai", "gemini", "openai"} and _has_key(db, settings, primary):
        return primary, requested_model or _default_model(settings, primary), ""
    fallback = (config.fallback_provider if config else "") or ""
    if fallback in {"xai", "gemini", "openai"} and _has_key(db, settings, fallback):
        model = (config.fallback_model if config else "") or _default_model(settings, fallback)
        return fallback, model, f"{primary} has no key; using {fallback}"
    return "", "", NO_LLM_PROVIDER


def provider_catalog(db: Session) -> list[dict]:
    from app.providers.secrets import secret_status

    settings = get_settings()
    env = {
        "xai": settings.xai_api_key,
        "gemini": settings.gemini_api_key,
        "openai": settings.openai_api_key,
        "tavily": settings.tavily_api_key or (settings.search_api_key if settings.search_provider in {"auto", "tavily"} else ""),
        "brave": settings.brave_api_key or (settings.search_api_key if settings.search_provider == "brave" else ""),
    }
    return [secret_status(db, name, env.get(name, "")) for name in ("xai", "gemini", "openai", "tavily", "brave")]


def _has_key(db, settings, provider: str) -> bool:
    env = {
        "xai": settings.xai_api_key,
        "gemini": settings.gemini_api_key,
        "openai": settings.openai_api_key,
    }[provider]
    return bool(resolve_secret(db, provider, env))


def _default_model(settings, provider: str) -> str:
    return {
        "xai": settings.xai_model,
        "gemini": settings.gemini_model,
        "openai": settings.openai_model,
    }.get(provider, DEFAULT_MODELS.get(provider, ""))


def parse_json_object(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Model did not return a JSON object")
    return value


def _openai_compatible(url: str, key: str, model: str, system: str, prompt: str, temperature: float, max_tokens: int) -> str:
    if not key:
        raise RuntimeError("missing API key")
    with httpx.Client(timeout=45) as client:
        response = client.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
    return payload["choices"][0]["message"]["content"]


def _gemini(key: str, model: str, system: str, prompt: str, temperature: float, max_tokens: int) -> str:
    if not key:
        raise RuntimeError("missing API key")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    with httpx.Client(timeout=45) as client:
        response = client.post(
            url,
            params={"key": key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "responseMimeType": "application/json",
                },
            },
        )
        response.raise_for_status()
        payload = response.json()
    return payload["candidates"][0]["content"]["parts"][0]["text"]
