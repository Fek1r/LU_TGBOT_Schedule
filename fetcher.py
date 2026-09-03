"""Cached, shared access to the scraper.

Every subscriber used to trigger their own request. With per-user groups that
would multiply fast, so requests are cached per (group, week) and de-duplicated
with a lock — fifty classmates asking at 07:00 is still one hit on the site.
"""
import asyncio
import logging
import time

from scraper import Lesson, fetch_schedule

logger = logging.getLogger(__name__)

_TTL = 300  # seconds; the university does not rewrite the timetable every minute

_cache: dict[tuple[str, int], tuple[float, list[Lesson]]] = {}
_locks: dict[tuple[str, int], asyncio.Lock] = {}


async def fetch(group_id: str, week_offset: int = 0, *, fresh: bool = False) -> list[Lesson]:
    """Lessons for one group and week. Raises whatever the scraper raises."""
    key = (group_id, week_offset)
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _cache.get(key)
        if cached and not fresh and time.time() - cached[0] < _TTL:
            return cached[1]
        lessons = await asyncio.to_thread(fetch_schedule, group_id, week_offset)
        _cache[key] = (time.time(), lessons)
        return lessons


def invalidate(group_id: str | None = None) -> None:
    for key in [k for k in _cache if group_id is None or k[0] == group_id]:
        _cache.pop(key, None)
