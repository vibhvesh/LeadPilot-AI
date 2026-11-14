"""Group server and browser errors. 401 and login redirects are not stored."""

import hashlib
import re
import time
import traceback

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.identity import utcnow
from app.models.perf import AppErrorEvent, AppErrorGroup

_OCCURRENCE_CAP = 30
_NOT_FOUND_CAP = 5
_HITS: dict[str, list[float]] = {}


def fingerprint(source: str, status: int, method: str, path: str, kind: str, message: str) -> str:
    clean = re.sub(r"/\d+", "/{id}", (path or "/").split("?", 1)[0])
    raw = "|".join([source, str(status), method.upper(), clean, kind, (message or "")[:180]])
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def allow_client_report(user_id: int, limit: int) -> bool:
    now = time.monotonic()
    key = str(user_id)
    recent = [stamp for stamp in _HITS.get(key, []) if now - stamp < 60]
    if len(recent) >= max(1, limit):
        _HITS[key] = recent
        return False
    recent.append(now)
    _HITS[key] = recent
    return True


def reset_rate_limit() -> None:
    _HITS.clear()


def record_error(
    db: Session,
    *,
    source: str,
    status: int,
    method: str,
    path: str,
    message: str,
    trace: str = "",
    user_id: int | None = None,
    request_id: str = "",
) -> AppErrorGroup:
    kind = "client" if source == "client" else ("http" if status < 500 else "exception")
    level = "client" if source == "client" else ("error" if status >= 500 else "warning")
    key = fingerprint(source, status, method, path, kind, message)
    group = db.scalar(select(AppErrorGroup).where(AppErrorGroup.fingerprint == key))
    now = utcnow()
    if group is None:
        group = AppErrorGroup(
            fingerprint=key,
            source=source,
            level=level,
            status_code=status,
            method=(method or "")[:12],
            path=(path or "")[:300],
            message=(message or "")[:500],
            sample_trace=(trace or "")[:8000],
            count=1,
            first_seen=now,
            last_seen=now,
        )
        db.add(group)
        db.flush()
    else:
        group.count += 1
        group.last_seen = now
        group.resolved = False
        group.resolved_at = None
        if trace and not group.sample_trace:
            group.sample_trace = trace[:8000]
    cap = _NOT_FOUND_CAP if status == 404 else _OCCURRENCE_CAP
    already = db.scalar(select(func.count()).select_from(AppErrorEvent).where(AppErrorEvent.group_id == group.id)) or 0
    if already < cap:
        db.add(
            AppErrorEvent(
                group_id=group.id,
                method=(method or "")[:12],
                path=(path or "")[:300],
                status_code=status,
                user_id=user_id,
                request_id=(request_id or "")[:64],
                traceback=(trace or "")[:8000],
                created_at=now,
            )
        )
    db.commit()
    return group


def format_exception(exc: BaseException) -> tuple[str, str]:
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return exc.__class__.__name__ + ": " + str(exc), text[-8000:]
