"""SQLAlchemy engine and session. SQLite for local demo, Postgres in production."""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

engine = None
SessionLocal = None


class Base(DeclarativeBase):
    pass


def init_database(url: str) -> None:
    global engine, SessionLocal
    if url.startswith("sqlite///") or url.startswith("sqlite:///"):
        raw = url.split("sqlite:///", 1)[-1]
        if raw and raw != ":memory:":
            Path(raw).parent.mkdir(parents=True, exist_ok=True)

    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool

    engine = create_engine(url, **kwargs)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    from app import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)
    _ensure_columns(engine)
    from app.social.schema import upgrade as upgrade_social
    from app.pulse.schema import upgrade as upgrade_pulse

    upgrade_social(engine)
    upgrade_pulse(engine)
    from app.mascot.schema import upgrade as upgrade_mascot

    upgrade_mascot(engine)


def _ensure_columns(bound) -> None:
    """Add columns introduced after an older database was created."""
    inspector = inspect(bound)
    dialect = bound.dialect
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing or column.primary_key:
                continue
            type_sql = column.type.compile(dialect=dialect)
            with bound.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {type_sql}"))


def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database is not initialized")
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def session_scope():
    if SessionLocal is None:
        raise RuntimeError("Database is not initialized")
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
