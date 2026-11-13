from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "LeadPilot AI"
    app_env: str = "development"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str
    super_admin_email: str = "vibhvesh@gmail.com"
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
