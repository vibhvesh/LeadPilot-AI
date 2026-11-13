"""LeadPilot HTTP application. The browser UI is served by this same service."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.agents.router import router as agents_router
from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.auth.service import user_from_request
from app.comments.router import router as comments_router
from app.core.config import get_settings
from app.core import database
from app.core.database import init_database, session_scope
from app.core.errors import AppError
from app.core.seed import seed
from app.dashboard.router import router as dashboard_router
from app.followups.router import router as followups_router
from app.leads.router import router as leads_router
from app.providers.router import router as providers_router
from app.search.router import router as search_router
from app.settings.router import router as settings_router
from app.users.router import router as users_router

WEB = Path(__file__).resolve().parent / "web"
PUBLIC_API = {"/api/auth/config"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    with session_scope() as db:
        seed(db, get_settings())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    init_database(settings.resolved_database_url())
    app = FastAPI(
        title="CanberraAI LeadPilot",
        version="1.0.0",
        description="Lead intelligence workspace for TMS-LEAD / LinkTMS",
        lifespan=lifespan,
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="leadpilot_oidc",
        max_age=600,
        same_site="lax",
        https_only=settings.session_cookie_secure,
    )

    @app.middleware("http")
    async def require_api_session(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and path not in PUBLIC_API:
            db = database.SessionLocal()
            try:
                user = user_from_request(db, request)
                status = user.status if user is not None else None
            finally:
                db.close()
            if user is None:
                return JSONResponse({"detail": "Sign-in required"}, status_code=401)
            if status != "approved":
                return JSONResponse({"detail": "Account is not approved"}, status_code=403)
        return await call_next(request)

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)

    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(leads_router)
    app.include_router(search_router)
    app.include_router(agents_router)
    app.include_router(providers_router)
    app.include_router(users_router)
    app.include_router(followups_router)
    app.include_router(comments_router)
    app.include_router(audit_router)
    app.include_router(settings_router)

    @app.get("/health")
    def health():
        from sqlalchemy import select

        db = database.SessionLocal()
        try:
            db.execute(select(1))
        finally:
            db.close()
        return {"status": "ok", "product": "CanberraAI LeadPilot"}

    @app.get("/")
    def home(request: Request):
        if not _approved(request):
            return RedirectResponse("/login", status_code=302)
        return FileResponse(WEB / "index.html")

    @app.get("/login")
    def login_page(request: Request):
        if _approved(request):
            return RedirectResponse("/", status_code=302)
        return FileResponse(WEB / "login.html")

    @app.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)

    app.mount("/static", StaticFiles(directory=WEB), name="static")
    return app


def _approved(request: Request) -> bool:
    db = database.SessionLocal()
    try:
        user = user_from_request(db, request)
        return user is not None and user.status == "approved"
    finally:
        db.close()


app = create_app()
