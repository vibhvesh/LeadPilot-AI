"""Session tokens and encryption helpers. Provider keys never leave the server."""

import base64
import hashlib
import secrets

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def new_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _fernet() -> Fernet:
    settings = get_settings()
    material = (settings.encryption_key or settings.session_secret).encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Stored secret could not be decrypted. Check ENCRYPTION_KEY.") from exc


def secret_hint(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) < 4:
        return "••••"
    return "••••" + cleaned[-4:]
