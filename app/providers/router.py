"""API key storage, provider access, and LLM routing. Keys are never returned."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_module
from app.models import LLMConfig
from app.providers.access import list_access, upsert_access, usage_snapshot
from app.providers.llm import provider_catalog, select_provider
from app.providers.secrets import delete_key, store_key

router = APIRouter(prefix="/api")

EDITABLE = ("xai", "gemini", "openai", "tavily", "brave")


@router.get("/providers")
def providers(db: Session = Depends(get_db), actor=Depends(require_module("apikeys"))):
    settings = get_settings()
    catalog = provider_catalog(db)
    access = list_access(db)
    usage = []
    for provider in ("xai", "gemini", "openai", "search", "mock"):
        usage.append(usage_snapshot(db, actor, provider))
    return {
        "keys": catalog,
        "access": access,
        "usage": usage,
        "search_provider_mode": settings.search_provider,
        "effective_llm": _llm_public(db),
    }


@router.put("/providers/keys")
def put_key(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("apikeys", manage=True))):
    provider = str(body.get("provider") or "").strip().lower()
    if provider not in EDITABLE:
        from app.core.errors import AppError

        raise AppError("Unknown provider")
    stored = store_key(db, provider, str(body.get("api_key") or ""), actor.id)
    record(db, user=actor, action="api_key_saved", module="apikeys", target=provider, detail={"hint": stored["hint"]})
    db.commit()
    return stored


@router.delete("/providers/keys/{provider}")
def remove_key(provider: str, db: Session = Depends(get_db), actor=Depends(require_module("apikeys", manage=True))):
    provider = provider.strip().lower()
    delete_key(db, provider)
    record(db, user=actor, action="api_key_deleted", module="apikeys", target=provider, detail={"database_copy_removed": True})
    db.commit()
    return {"provider": provider, "database_copy_removed": True}


@router.put("/providers/access")
def put_access(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("apikeys", manage=True))):
    saved = upsert_access(db, body)
    record(
        db,
        user=actor,
        action="permission_change",
        module="apikeys",
        target=saved["provider"],
        detail={key: saved[key] for key in ("role", "user_id", "enabled", "daily_quota", "monthly_quota")},
    )
    db.commit()
    return saved


@router.get("/ai/config")
def get_ai(db: Session = Depends(get_db), _user=Depends(require_module("ai"))):
    config = _config(db)
    return {**_config_dict(config), "effective": _llm_public(db)}


@router.put("/ai/config")
def put_ai(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("ai", manage=True))):
    config = _config(db)
    primary = str(body.get("primary_provider") or "auto").strip().lower()
    fallback = str(body.get("fallback_provider") or "mock").strip().lower()
    allowed = {"auto", "mock", "xai", "gemini", "openai"}
    if primary not in allowed or fallback not in allowed:
        from app.core.errors import AppError

        raise AppError("Unknown model provider")
    config.primary_provider = primary
    config.primary_model = str(body.get("primary_model") or "").strip()[:120]
    config.fallback_provider = fallback
    config.fallback_model = str(body.get("fallback_model") or "").strip()[:120]
    try:
        config.temperature = float(body.get("temperature", config.temperature))
    except (TypeError, ValueError):
        config.temperature = 0.2
    try:
        config.max_tokens = int(body.get("max_tokens", config.max_tokens))
    except (TypeError, ValueError):
        config.max_tokens = 1200
    record(db, user=actor, action="settings_change", module="ai", target=primary, detail={"fallback": fallback, "model": config.primary_model})
    db.commit()
    return {**_config_dict(config), "effective": _llm_public(db)}


def _config(db: Session) -> LLMConfig:
    config = db.get(LLMConfig, 1)
    if config is None:
        config = LLMConfig(id=1, primary_provider="auto", fallback_provider="mock")
        db.add(config)
        db.flush()
    return config


def _config_dict(config: LLMConfig) -> dict:
    return {
        "primary_provider": config.primary_provider,
        "primary_model": config.primary_model or "",
        "fallback_provider": config.fallback_provider,
        "fallback_model": config.fallback_model or "",
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }


def _llm_public(db: Session) -> dict:
    provider, model, note = select_provider(db)
    return {"provider": provider, "model": model, "note": note}
