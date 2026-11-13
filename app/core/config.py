"""Environment configuration. Secrets stay in the environment, never in code."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/leadpilot.db"
    session_secret: str = ""
    session_cookie_name: str = "leadpilot_session"
    session_max_age_seconds: int = 28800
    session_cookie_secure: bool = False
    demo_mode: bool = False
    super_admin_email: str = "vibhvesh@gmail.com"
    public_base_url: str = "http://localhost:8000"
    encryption_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_discovery_url: str = "https://accounts.google.com/.well-known/openid-configuration"
    google_redirect_uri: str = ""

    search_provider: str = "auto"
    search_api_key: str = ""
    tavily_api_key: str = ""
    brave_api_key: str = ""

    xai_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    xai_model: str = "grok-3"
    gemini_model: str = "gemini-2.0-flash"
    openai_model: str = "gpt-4o-mini"
    ai_search_max_rounds: int = 2
    grokbot_webhook_url: str = ""
    grokbot_webhook_secret: str = ""

    @property
    def super_admin(self) -> str:
        return self.super_admin_email.strip().lower()

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id.strip() and self.google_client_secret.strip())

    def resolved_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://") :]
        if url.startswith("postgresql://") and "+psycopg" not in url.split("://", 1)[0]:
            return "postgresql+psycopg://" + url[len("postgresql://") :]
        return url

    def redirect_uri(self) -> str:
        if self.google_redirect_uri.strip():
            return self.google_redirect_uri.strip()
        return self.public_base_url.rstrip("/") + "/auth/google/callback"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if len(settings.session_secret) < 32:
        if settings.demo_mode or settings.app_env in {"development", "test"}:
            settings.session_secret = "dev-only-session-secret-change-before-production"
        else:
            raise RuntimeError("SESSION_SECRET must contain at least 32 characters.")
    return settings
