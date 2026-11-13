"""Resolve provider secrets from the environment first, then encrypted rows."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_secret, encrypt_secret, secret_hint
from app.models import ProviderKey


def resolve_secret(db: Session | None, provider: str, env_value: str = "") -> str | None:
    if env_value and env_value.strip():
        return env_value.strip()
    if db is None:
        return None
    row = db.scalar(select(ProviderKey).where(ProviderKey.provider == provider))
    if row is None or not row.ciphertext:
        return None
    return decrypt_secret(row.ciphertext)


def secret_status(db: Session, provider: str, env_value: str = "") -> dict:
    row = db.scalar(select(ProviderKey).where(ProviderKey.provider == provider))
    if env_value and env_value.strip():
        return {
            "provider": provider,
            "configured": True,
            "source": "environment",
            "hint": secret_hint(env_value),
            "database_copy": row is not None,
        }
    if row is None:
        return {"provider": provider, "configured": False, "source": "missing", "hint": "", "database_copy": False}
    return {
        "provider": provider,
        "configured": True,
        "source": "database",
        "hint": row.hint,
        "database_copy": True,
    }


def store_key(db: Session, provider: str, api_key: str, user_id: int | None) -> dict:
    cleaned = (api_key or "").strip()
    if len(cleaned) < 8:
        from app.core.errors import AppError

        raise AppError("Enter the provider API key")
    row = db.scalar(select(ProviderKey).where(ProviderKey.provider == provider))
    if row is None:
        row = ProviderKey(provider=provider, ciphertext=encrypt_secret(cleaned), hint=secret_hint(cleaned), created_by=user_id)
        db.add(row)
    else:
        row.ciphertext = encrypt_secret(cleaned)
        row.hint = secret_hint(cleaned)
        row.created_by = user_id
    db.flush()
    return {"provider": provider, "hint": row.hint, "stored": True}


def delete_key(db: Session, provider: str) -> None:
    row = db.scalar(select(ProviderKey).where(ProviderKey.provider == provider))
    if row is not None:
        db.delete(row)
