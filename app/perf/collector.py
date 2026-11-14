"""Read the host and write one perf_samples row. Older rows are deleted on the same pass."""

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psutil
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import engine
from app.models.identity import utcnow
from app.models.perf import AppErrorEvent, AppErrorGroup, PerfSample
from app.perf.stats import STATS

_LAST_DISK = None
_LAST_NET = None
_LAST_AT = None


def collect_sample(db: Session) -> PerfSample:
    global _LAST_DISK, _LAST_NET, _LAST_AT
    now = time.monotonic()
    cpu = psutil.cpu_percent(interval=None)
    try:
        load = psutil.getloadavg()
    except (OSError, AttributeError):
        load = (0.0, 0.0, 0.0)
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    root = _disk("/")
    app_path = _app_mount()
    app_disk = root if app_path == "/" else _disk(app_path)
    read_bps, write_bps = _disk_rates(now)
    rx_bps, tx_bps = _net_rates(now)
    _LAST_AT = now
    process = psutil.Process(os.getpid())
    try:
        process_cpu = process.cpu_percent(interval=None)
    except Exception:
        process_cpu = 0.0
    rss = int(getattr(process.memory_info(), "rss", 0) or 0)
    connections, size = _database(db)
    minute = STATS.snapshot(reset=True)
    row = PerfSample(
        sampled_at=utcnow(),
        cpu_percent=float(cpu or 0),
        load_1=float(load[0]),
        load_5=float(load[1]),
        load_15=float(load[2]),
        memory_used=int(memory.used),
        memory_total=int(memory.total),
        memory_percent=float(memory.percent),
        swap_used=int(swap.used),
        swap_total=int(swap.total),
        swap_percent=float(swap.percent or 0),
        disk_root_percent=root,
        disk_app_percent=app_disk,
        disk_read_bps=read_bps,
        disk_write_bps=write_bps,
        net_rx_bps=rx_bps,
        net_tx_bps=tx_bps,
        process_rss=rss,
        process_cpu=float(process_cpu or 0),
        db_connections=connections,
        db_size_bytes=size,
        request_count=minute["request_count"],
        error_count=minute["error_count"],
        latency_p50=minute["latency_p50"],
        latency_p95=minute["latency_p95"],
        latency_p99=minute["latency_p99"],
        slowest=minute["slowest"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def purge(db: Session, perf_days: int | None = None, error_days: int | None = None) -> dict:
    settings = get_settings()
    perf_days = settings.perf_retention_days if perf_days is None else perf_days
    error_days = settings.error_retention_days if error_days is None else error_days
    now = utcnow()
    perf_cut = _stamp(now - timedelta(days=max(1, int(perf_days))))
    error_cut = _stamp(now - timedelta(days=max(1, int(error_days))))
    options = {"synchronize_session": False}
    samples = db.execute(delete(PerfSample).where(PerfSample.sampled_at < perf_cut), execution_options=options).rowcount or 0
    events = db.execute(delete(AppErrorEvent).where(AppErrorEvent.created_at < error_cut), execution_options=options).rowcount or 0
    groups = db.execute(delete(AppErrorGroup).where(AppErrorGroup.last_seen < error_cut), execution_options=options).rowcount or 0
    db.commit()
    return {"samples": samples, "events": events, "groups": groups}


def _stamp(moment: datetime) -> datetime:
    """SQLite returns naive timestamps. Compare those with a naive UTC cutoff."""
    if engine is not None and engine.dialect.name == "sqlite":
        return moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment


def _disk(path: str) -> float:
    try:
        return float(psutil.disk_usage(path).percent)
    except OSError:
        return 0.0


def _app_mount() -> str:
    candidates = [Path("/app"), Path.cwd()]
    settings = get_settings()
    url = settings.resolved_database_url()
    if url.startswith("sqlite"):
        raw = url.split("sqlite:///", 1)[-1]
        if raw and raw != ":memory:":
            candidates.insert(0, Path(raw).resolve().parent)
    for path in candidates:
        if path.exists():
            return str(path)
    return "/"


def _disk_rates(now: float) -> tuple[float, float]:
    global _LAST_DISK
    counters = psutil.disk_io_counters()
    if counters is None or _LAST_DISK is None or _LAST_AT is None:
        _LAST_DISK = counters
        return 0.0, 0.0
    elapsed = max(now - _LAST_AT, 0.001)
    read = max(0, counters.read_bytes - _LAST_DISK.read_bytes) / elapsed
    write = max(0, counters.write_bytes - _LAST_DISK.write_bytes) / elapsed
    _LAST_DISK = counters
    return round(read, 1), round(write, 1)


def _net_rates(now: float) -> tuple[float, float]:
    global _LAST_NET
    counters = psutil.net_io_counters()
    if _LAST_NET is None or _LAST_AT is None:
        _LAST_NET = counters
        return 0.0, 0.0
    elapsed = max(now - _LAST_AT, 0.001)
    rx = max(0, counters.bytes_recv - _LAST_NET.bytes_recv) / elapsed
    tx = max(0, counters.bytes_sent - _LAST_NET.bytes_sent) / elapsed
    _LAST_NET = counters
    return round(rx, 1), round(tx, 1)


def _database(db: Session) -> tuple[int, int]:
    url = str(engine.url) if engine is not None else ""
    if url.startswith("postgres"):
        try:
            connections = db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")).scalar() or 0
            size = db.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0
            return int(connections), int(size)
        except Exception:
            db.rollback()
            return 0, 0
    size = 0
    if url.startswith("sqlite"):
        raw = url.split("///", 1)[-1]
        if raw and raw != ":memory:" and Path(raw).exists():
            size = Path(raw).stat().st_size
    pool = getattr(engine, "pool", None)
    connections = 0
    if pool is not None:
        checked = getattr(pool, "checkedout", None)
        idle = getattr(pool, "checkedin", None)
        if callable(checked):
            connections += int(checked() or 0)
        if callable(idle):
            connections += int(idle() or 0)
    return connections, int(size)
