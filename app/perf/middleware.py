"""Time each HTTP request and store 4xx and 5xx responses people actually see."""

import time
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth.service import user_from_raw_token
from app.core import database
from app.core.config import get_settings
from app.perf.errors import format_exception, record_error
from app.perf.stats import STATS

_SKIP_STATUS = {401, 302, 301, 303, 307, 308}
_SKIP_PREFIXES = ("/static/", "/favicon.ico")


class PerfMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        started = time.perf_counter()
        status = 500
        path = scope.get("path") or "/"

        async def observe(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, observe)
        except Exception as exc:
            message, trace = format_exception(exc)
            _store(scope, 500, path, message, trace, request_id)
            STATS.record(path, 500, (time.perf_counter() - started) * 1000)
            response = JSONResponse({"detail": "Server error", "request_id": request_id}, status_code=500)
            response.headers["X-Request-Id"] = request_id
            await response(scope, receive, send)
            return
        elapsed = (time.perf_counter() - started) * 1000
        if not path.startswith(_SKIP_PREFIXES):
            STATS.record(path, status, elapsed)
        if status in _SKIP_STATUS or status < 400 or path.startswith(_SKIP_PREFIXES):
            return
        if path == "/api/client-errors":
            return
        _store(scope, status, path, f"HTTP {status}", "", request_id)


def _store(scope, status: int, path: str, message: str, trace: str, request_id: str) -> None:
    if database.SessionLocal is None:
        return
    db = database.SessionLocal()
    try:
        user_id = _user_id(scope, db)
        record_error(
            db,
            source="server",
            status=status,
            method=scope.get("method") or "",
            path=path,
            message=message,
            trace=trace,
            user_id=user_id,
            request_id=request_id,
        )
    except Exception:
        db.rollback()
    finally:
        db.close()


def _user_id(scope, db) -> int | None:
    request = Request(scope)
    settings = get_settings()
    raw = request.cookies.get(settings.session_cookie_name)
    user = user_from_raw_token(db, raw)
    return user.id if user is not None else None
