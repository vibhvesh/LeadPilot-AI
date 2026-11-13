import secrets
from hashlib import sha256

def new_session_token() -> str:
    """Generate a high-entropy opaque token; persist only its hash."""
    return secrets.token_urlsafe(48)

def token_digest(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
