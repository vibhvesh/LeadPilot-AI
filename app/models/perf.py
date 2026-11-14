"""Performance samples and stored application errors."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import utcnow


class PerfSample(Base):
    __tablename__ = "perf_samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    cpu_percent: Mapped[float] = mapped_column(Float, default=0)
    load_1: Mapped[float] = mapped_column(Float, default=0)
    load_5: Mapped[float] = mapped_column(Float, default=0)
    load_15: Mapped[float] = mapped_column(Float, default=0)
    memory_used: Mapped[int] = mapped_column(BigInteger, default=0)
    memory_total: Mapped[int] = mapped_column(BigInteger, default=0)
    memory_percent: Mapped[float] = mapped_column(Float, default=0)
    swap_used: Mapped[int] = mapped_column(BigInteger, default=0)
    swap_total: Mapped[int] = mapped_column(BigInteger, default=0)
    swap_percent: Mapped[float] = mapped_column(Float, default=0)
    disk_root_percent: Mapped[float] = mapped_column(Float, default=0)
    disk_app_percent: Mapped[float] = mapped_column(Float, default=0)
    disk_read_bps: Mapped[float] = mapped_column(Float, default=0)
    disk_write_bps: Mapped[float] = mapped_column(Float, default=0)
    net_rx_bps: Mapped[float] = mapped_column(Float, default=0)
    net_tx_bps: Mapped[float] = mapped_column(Float, default=0)
    process_rss: Mapped[int] = mapped_column(BigInteger, default=0)
    process_cpu: Mapped[float] = mapped_column(Float, default=0)
    db_connections: Mapped[int] = mapped_column(Integer, default=0)
    db_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_p50: Mapped[float] = mapped_column(Float, default=0)
    latency_p95: Mapped[float] = mapped_column(Float, default=0)
    latency_p99: Mapped[float] = mapped_column(Float, default=0)
    slowest: Mapped[list] = mapped_column(JSON, default=list)


class AppErrorGroup(Base):
    __tablename__ = "app_error_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(20), default="server", index=True)
    level: Mapped[str] = mapped_column(String(20), default="error", index=True)
    status_code: Mapped[int] = mapped_column(Integer, default=500, index=True)
    method: Mapped[str] = mapped_column(String(12), default="")
    path: Mapped[str] = mapped_column(String(300), default="", index=True)
    message: Mapped[str] = mapped_column(String(500), default="")
    sample_trace: Mapped[str] = mapped_column(Text, default="")
    count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str] = mapped_column(String(320), default="")


class AppErrorEvent(Base):
    """One occurrence. 404s past a small cap only increment the group count."""

    __tablename__ = "app_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("app_error_groups.id"), index=True)
    method: Mapped[str] = mapped_column(String(12), default="")
    path: Mapped[str] = mapped_column(String(300), default="")
    status_code: Mapped[int] = mapped_column(Integer, default=500)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    traceback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
