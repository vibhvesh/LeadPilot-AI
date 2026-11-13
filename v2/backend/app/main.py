from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.database import engine
from app.auth.router import router as auth_router
from app.admin.router import router as admin_router

app = FastAPI(title=settings.app_name, version="2.0.0")
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type", "X-Request-ID"])

app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "leadpilot-api", "version": "2.0.0"}

@app.get("/ready", tags=["system"])
def readiness():
    checks = {"database": "ok", "redis": "ok"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        checks["database"] = "error"
    try:
        Redis.from_url(settings.redis_url, socket_connect_timeout=1).ping()
    except RedisError:
        checks["redis"] = "error"
    ready = all(value == "ok" for value in checks.values())
    return {"status": "ready" if ready else "not_ready", "checks": checks}
