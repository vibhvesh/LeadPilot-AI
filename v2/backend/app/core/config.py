from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "LeadPilot AI"
    app_env: str = "development"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str
    super_admin_email: str = "vibhvesh@gmail.com"
    cors_origins: str = "https://leads.canberravision.com"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "https://leads.canberravision.com/api/v1/auth/google/callback"
    frontend_url: str = "https://leads.canberravision.com"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
