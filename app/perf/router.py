"""Admin performance and error-log APIs, plus the authenticated client-error intake."""

import json
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import engine, get_db
from app.core.deps import get_current_user
from app.models.identity import utcnow
from app.models.perf import AppErrorEvent, AppErrorGroup, PerfSample
from app.perf.errors import allow_client_report, record_error
from app.perf.stats import STARTED, STATS

router = APIRouter()
RANGES = {"1h": 1, "6h": 6, "24h": 24, "3d": 72, "5d": 120}


def require_admin(user=Depends(get_current_user)):
    if user.role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def _sample(row: PerfSample) -> dict:
    return {
        "sampled_at": row.sampled_at.isoformat() if row.sampled_at else None,
        "cpu_percent": row.cpu_percent,
        "load_1": row.load_1,
        "load_5": row.load_5,
        "load_15": row.load_15,
        "memory_used": row.memory_used,
        "memory_total": row.memory_total,
        "memory_percent": row.memory_percent,
        "swap_used": row.swap_used,
        "swap_total": row.swap_total,
        "swap_percent": row.swap_percent,
        "disk_root_percent": row.disk_root_percent,
        "disk_app_percent": row.disk_app_percent,
        "disk_read_bps": row.disk_read_bps,
        "disk_write_bps": row.disk_write_bps,
        "net_rx_bps": row.net_rx_bps,
        "net_tx_bps": row.net_tx_bps,
        "process_rss": row.process_rss,
        "process_cpu": row.process_cpu,
        "db_connections": row.db_connections,
        "db_size_bytes": row.db_size_bytes,
        "request_count": row.request_count,
        "error_count": row.error_count,
        "latency_p50": row.latency_p50,
        "latency_p95": row.latency_p95,
        "latency_p99": row.latency_p99,
        "slowest": row.slowest or [],
    }


def _stamp(moment: datetime) -> datetime:
    if engine is not None and engine.dialect.name == "sqlite":
        return moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment


def _day(value: str | None, end: bool) -> datetime | None:
    if not value:
        return None
    try:
        day = datetime.fromisoformat(value[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return _stamp(day + timedelta(days=1) if end else day)


def _group(row: AppErrorGroup) -> dict:
    return {
        "id": row.id,
        "fingerprint": row.fingerprint,
        "source": row.source,
        "level": row.level,
        "status_code": row.status_code,
        "method": row.method,
        "path": row.path,
        "message": row.message,
        "count": row.count,
        "first_seen": row.first_seen.isoformat() if row.first_seen else None,
        "last_seen": row.last_seen.isoformat() if row.last_seen else None,
        "resolved": row.resolved,
    }


@router.get("/api/admin/perf/current")
def current(_user=Depends(require_admin), db: Session = Depends(get_db)):
    row = db.scalars(select(PerfSample).order_by(PerfSample.id.desc()).limit(1)).first()
    live = STATS.snapshot(reset=False)
    return {
        "uptime_seconds": int(time.time() - STARTED),
        "live": live,
        "sample": _sample(row) if row is not None else None,
    }


@router.get("/api/admin/perf/history")
def history(range: str = "1h", _user=Depends(require_admin), db: Session = Depends(get_db)):
    hours = RANGES.get(range, 1)
    since = _stamp(utcnow() - timedelta(hours=hours))
    rows = db.scalars(select(PerfSample).where(PerfSample.sampled_at >= since).order_by(PerfSample.sampled_at.asc())).all()
    if len(rows) > 180:
        step = max(1, len(rows) // 180)
        rows = rows[::step]
    return {"range": range if range in RANGES else "1h", "samples": [_sample(row) for row in rows]}


@router.get("/api/admin/errors")
def errors(
    level: str | None = None,
    source: str | None = None,
    path: str | None = None,
    user_id: int | None = None,
    since: str | None = None,
    until: str | None = None,
    resolved: str | None = None,
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    statement = select(AppErrorGroup).order_by(AppErrorGroup.last_seen.desc()).limit(200)
    if level:
        statement = statement.where(AppErrorGroup.level == level)
    if source:
        statement = statement.where(AppErrorGroup.source == source)
    if path:
        statement = statement.where(AppErrorGroup.path.contains(path[:200]))
    start = _day(since, end=False)
    finish = _day(until, end=True)
    if start is not None:
        statement = statement.where(AppErrorGroup.last_seen >= start)
    if finish is not None:
        statement = statement.where(AppErrorGroup.last_seen < finish)
    if resolved in {"true", "false"}:
        statement = statement.where(AppErrorGroup.resolved.is_(resolved == "true"))
    if user_id is not None:
        ids = db.scalars(select(AppErrorEvent.group_id).where(AppErrorEvent.user_id == user_id).distinct()).all()
        statement = statement.where(AppErrorGroup.id.in_(ids or [-1]))
    return {"errors": [_group(row) for row in db.scalars(statement).all()]}


@router.get("/api/admin/errors/{group_id}")
def error_detail(group_id: int, _user=Depends(require_admin), db: Session = Depends(get_db)):
    group = db.get(AppErrorGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Error group not found")
    events = db.scalars(
        select(AppErrorEvent).where(AppErrorEvent.group_id == group.id).order_by(AppErrorEvent.id.desc()).limit(20)
    ).all()
    payload = _group(group)
    payload["sample_trace"] = group.sample_trace or ""
    payload["occurrences"] = [
        {
            "id": event.id,
            "path": event.path,
            "method": event.method,
            "status_code": event.status_code,
            "user_id": event.user_id,
            "request_id": event.request_id,
            "traceback": event.traceback or "",
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in events
    ]
    return payload


@router.post("/api/admin/errors/{group_id}/resolve")
def resolve_error(group_id: int, body: dict, user=Depends(require_admin), db: Session = Depends(get_db)):
    group = db.get(AppErrorGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Error group not found")
    group.resolved = bool((body or {}).get("resolved", True))
    group.resolved_at = utcnow() if group.resolved else None
    group.resolved_by = user.email if group.resolved else ""
    db.commit()
    return _group(group)


@router.post("/api/client-errors")
async def client_errors(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    raw = await request.body()
    if len(raw) > 8000:
        raise HTTPException(status_code=413, detail="Error report is too large")
    if not allow_client_report(user.id, get_settings().client_error_per_minute):
        raise HTTPException(status_code=429, detail="Too many error reports")
    try:
        payload = json.loads(raw.decode() or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Send the error as JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Send the error as JSON")
    message = str(payload.get("message") or "Browser error")[:500]
    trace = str(payload.get("stack") or "")[:4000]
    path = str(payload.get("path") or request.headers.get("referer") or "")[:300]
    record_error(
        db,
        source="client",
        status=0,
        method="",
        path=path,
        message=message,
        trace=trace,
        user_id=user.id,
        request_id=str(request.scope.get("state", {}).get("request_id") or ""),
    )
    return {"stored": True}
