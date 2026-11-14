"""Background sampler. Tests call collect_sample directly and leave this off."""

import asyncio

from app.core.config import get_settings
from app.core.database import session_scope
from app.perf.collector import collect_sample, purge


async def run_sampler() -> None:
    while True:
        settings = get_settings()
        delay = min(60, max(30, int(settings.perf_sample_seconds or 45)))
        try:
            with session_scope() as db:
                collect_sample(db)
                purge(db)
        except Exception:
            pass
        await asyncio.sleep(delay)
