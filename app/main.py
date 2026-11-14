"""LeadPilot HTTP application. The browser UI is served by this same service."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.agents.router import router as agents_router
from app.ai_search.router import router as ai_search_router
from app.bot.admin_router import router as bot_admin_router
from app.bot.router import router as bot_router
from app.bot.talk_router import router as talk_router
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
from app.mascot.router import router as mascot_router
from app.perf.router import router as perf_router
from app.providers.router import router as providers_router
from app.search.router import router as search_router
from app.settings.router import router as settings_router
from app.social.bot_router import router as social_bot_router
from app.social.router import router as social_router
from app.pulse.bot_router import router as pulse_bot_router
from app.pulse.router import router as pulse_router
from app.users.router import router as users_router

WEB = Path(__file__).resolve().parent / "web"
PUBLIC_API = {"/api/auth/config"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import asyncio

    with session_scope() as db:
        seed(db, get_settings())
    task = None
    if get_settings().app_env != "test":
        from app.perf.loop import run_sampler

        task = asyncio.create_task(run_sampler())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()


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
        if path.startswith("/api/bot/"):
            return await call_next(request)
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
    app.include_router(mascot_router)
    app.include_router(search_router)
    app.include_router(ai_search_router)
    app.include_router(bot_router)
    app.include_router(talk_router)
    app.include_router(bot_admin_router)
    app.include_router(agents_router)
    app.include_router(providers_router)
    app.include_router(users_router)
    app.include_router(perf_router)
    app.include_router(followups_router)
    app.include_router(comments_router)
    app.include_router(audit_router)
    app.include_router(settings_router)
    app.include_router(social_router)
    app.include_router(social_bot_router)
    app.include_router(pulse_router)
    app.include_router(pulse_bot_router)

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
        return _workspace(request)

    @app.get("/social")
    def social_page(request: Request):
        return _workspace(request)

    @app.get("/pulse")
    def pulse_page(request: Request):
        return _workspace(request)

    @app.get("/leads")
    def leads_page(request: Request):
        """Deep link for a lead or a status column. The page reads ?id= and ?status=."""
        return _workspace(request)

    @app.get("/games")
    def games_page(request: Request):
        """Chess tab. Same shell as the rest of the workspace."""
        return _workspace(request)

    @app.get("/admin/performance")
    def performance_page(request: Request):
        if not _approved(request):
            return RedirectResponse("/login", status_code=302)
        if not _is_admin(request):
            return JSONResponse({"detail": "Admin only"}, status_code=403)
        return _workspace(request)

    @app.get("/login")
    def login_page(request: Request):
        if _approved(request):
            return RedirectResponse("/", status_code=302)
        return FileResponse(WEB / "login.html")

    @app.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)

    from app.perf.middleware import PerfMiddleware

    app.add_middleware(PerfMiddleware)
    app.mount("/static", StaticFiles(directory=WEB), name="static")
    return app


_CHESS_ORIGIN = "https://vibhvesh.github.io"


def _is_admin(request: Request) -> bool:
    db = database.SessionLocal()
    try:
        user = user_from_request(db, request)
        return user is not None and user.role in {"admin", "super_admin"}
    finally:
        db.close()


def _approved(request: Request) -> bool:
    db = database.SessionLocal()
    try:
        user = user_from_request(db, request)
        return user is not None and user.status == "approved"
    finally:
        db.close()


def _workspace(request: Request):
    if not _approved(request):
        return RedirectResponse("/login", status_code=302)
    response = FileResponse(WEB / "index.html")
    _allow_chess_embed(response)
    return response


def _allow_chess_embed(response: Response) -> None:
    """Allow the chess iframe, including microphone for push-to-talk."""
    origin = _CHESS_ORIGIN
    response.headers["Permissions-Policy"] = _merge_permissions(
        response.headers.get("permissions-policy", ""),
        ("microphone", "autoplay", "clipboard-write"),
        origin,
    )
    response.headers["Content-Security-Policy"] = _merge_frame_src(
        response.headers.get("content-security-policy", ""),
        origin,
    )


def _merge_permissions(policy: str, features: tuple, origin: str) -> str:
    items = []
    seen = set()
    for chunk in [part.strip() for part in policy.split(",") if part.strip()]:
        name = chunk.split("=", 1)[0].strip().lower()
        if name in features:
            seen.add(name)
            allowlist = chunk.split("=", 1)[-1]
            if origin in chunk or "*" in allowlist:
                items.append(chunk)
            elif chunk.rstrip().endswith(")"):
                body = chunk.rstrip()[:-1].rstrip()
                items.append(f'{body} "{origin}")' if not body.endswith("=") else f'{name}=(self "{origin}")')
            else:
                items.append(f'{name}=(self "{origin}")')
        else:
            items.append(chunk)
    for name in features:
        if name not in seen:
            items.append(f'{name}=(self "{origin}")')
    return ", ".join(items)


def _merge_frame_src(policy: str, origin: str) -> str:
    if not policy.strip():
        return f"frame-src 'self' {origin}"
    parts = [part.strip() for part in policy.split(";") if part.strip()]
    frame_tokens = None
    default_tokens = None
    kept = []
    for part in parts:
        tokens = part.split()
        name = tokens[0].lower()
        if name == "frame-src":
            frame_tokens = tokens[1:]
            continue
        if name == "default-src":
            default_tokens = tokens[1:]
        kept.append(part)
    if frame_tokens is None and default_tokens is None:
        return policy
    sources = [token for token in (frame_tokens if frame_tokens is not None else default_tokens) if token != "'none'"]
    if origin not in sources and "*" not in sources:
        sources.append(origin)
    if not sources:
        sources = [origin]
    kept.append("frame-src " + " ".join(sources))
    return "; ".join(kept)


app = create_app()
