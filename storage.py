"""
SQLite storage via aiosqlite.
Tables:
  subscribers    — one row per Telegram chat_id
  schedule_state — persisted lesson states for cancellation detection
"""
import logging
import os
from pathlib import Path

import aiosqlite

from scraper import Lesson

logger  = logging.getLogger(__name__)
DB_PATH = Path(os.getenv("DB_PATH", "bot.db"))


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id    INTEGER PRIMARY KEY,
                is_active  INTEGER NOT NULL DEFAULT 1,
                language   TEXT    NOT NULL DEFAULT 'ru',
                joined_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS schedule_state (
                uid   TEXT PRIMARY KEY,
                state TEXT NOT NULL
            );
        """)
        await db.commit()


async def get_subscriber(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT chat_id, is_active, language FROM subscribers WHERE chat_id = ?",
            (chat_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def upsert_subscriber(chat_id: int, language: str = "ru") -> bool:
    """Insert or reactivate subscriber. Returns True if newly subscribed."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_active FROM subscribers WHERE chat_id = ?", (chat_id,)
        ) as cur:
            row = await cur.fetchone()

        if row is None:
            await db.execute(
                "INSERT INTO subscribers (chat_id, language) VALUES (?, ?)",
                (chat_id, language),
            )
            await db.commit()
            return True

        if row[0] == 0:
            await db.execute(
                "UPDATE subscribers SET is_active = 1 WHERE chat_id = ?", (chat_id,)
            )
            await db.commit()
            return True

        return False  # already active


async def set_language(chat_id: int, language: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscribers SET language = ? WHERE chat_id = ?", (language, chat_id)
        )
        await db.commit()


async def deactivate(chat_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscribers SET is_active = 0 WHERE chat_id = ?", (chat_id,)
        )
        await db.commit()


async def get_active_subscribers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT chat_id, language FROM subscribers WHERE is_active = 1"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def find_newly_cancelled(lessons: list[Lesson]) -> list[Lesson]:
    """
    Compare current lesson states against stored states.
    Returns lessons that newly changed to 'Cancelled'.
    Updates stored states as a side-effect.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        uids = [l.uid for l in lessons]
        placeholders = ",".join("?" * len(uids))
        async with db.execute(
            f"SELECT uid, state FROM schedule_state WHERE uid IN ({placeholders})",
            uids,
        ) as cur:
            prev_states: dict[str, str] = {row[0]: row[1] async for row in cur}

        changed: list[Lesson] = []
        for lesson in lessons:
            if lesson.is_cancelled and prev_states.get(lesson.uid) != "Cancelled":
                changed.append(lesson)

        await db.executemany(
            "INSERT INTO schedule_state (uid, state) VALUES (?, ?)"
            " ON CONFLICT(uid) DO UPDATE SET state = excluded.state",
            [(l.uid, l.state) for l in lessons],
        )
        await db.commit()

    return changed
