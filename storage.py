"""
SQLite storage via aiosqlite.
Tables:
  subscribers    — one row per Telegram chat_id, including its chosen group
  schedule_state — persisted lesson states for cancellation detection
"""
import logging
import os
from pathlib import Path

import aiosqlite

import config
from scraper import Lesson

logger  = logging.getLogger(__name__)
DB_PATH = Path(os.getenv("DB_PATH", "bot.db"))


async def _migrate(db: aiosqlite.Connection) -> None:
    """Additive, idempotent schema catch-up for databases created earlier."""
    async with db.execute("PRAGMA table_info(subscribers)") as cur:
        columns = {row[1] async for row in cur}
    for column in ("group_id", "roster_ref"):
        if column not in columns:
            await db.execute(f"ALTER TABLE subscribers ADD COLUMN {column} TEXT")
            logger.info("Migrated subscribers: added %s", column)


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
        await _migrate(db)
        await db.commit()


def _with_default(row: dict) -> dict:
    row["group_id"] = row.get("group_id") or config.GROUP_ID
    return row


async def get_subscriber(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT chat_id, is_active, language, group_id, roster_ref FROM subscribers WHERE chat_id = ?",
            (chat_id,),
        ) as cur:
            row = await cur.fetchone()
            return _with_default(dict(row)) if row else None


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


async def set_group(chat_id: int, group_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscribers SET group_id = ? WHERE chat_id = ?", (group_id, chat_id)
        )
        await db.commit()


async def set_roster(chat_id: int, roster_ref: str | None) -> None:
    """Pin this chat to one person in the faculty roster — or unpin it."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscribers SET roster_ref = ? WHERE chat_id = ?", (roster_ref, chat_id)
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
            "SELECT chat_id, language, group_id, roster_ref FROM subscribers WHERE is_active = 1"
        ) as cur:
            return [_with_default(dict(r)) for r in await cur.fetchall()]


async def active_group_ids() -> list[str]:
    """Every distinct group someone is actually subscribed to."""
    return sorted({sub["group_id"] for sub in await get_active_subscribers()})


async def find_newly_cancelled(group_id: str, lessons: list[Lesson]) -> list[Lesson]:
    """
    Compare current lesson states against stored states.
    Returns lessons that newly changed to 'Cancelled'.
    Updates stored states as a side-effect.

    State keys are namespaced by group: the same lesson uid shows up in several
    groups, and one group's bookkeeping must not answer for another's.
    """
    def key(lesson: Lesson) -> str:
        return f"{group_id}|{lesson.uid}"

    async with aiosqlite.connect(DB_PATH) as db:
        keys = [key(l) for l in lessons]
        placeholders = ",".join("?" * len(keys))
        async with db.execute(
            f"SELECT uid, state FROM schedule_state WHERE uid IN ({placeholders})",
            keys,
        ) as cur:
            prev_states: dict[str, str] = {row[0]: row[1] async for row in cur}

        changed: list[Lesson] = []
        for lesson in lessons:
            if lesson.is_cancelled and prev_states.get(key(lesson)) != "Cancelled":
                changed.append(lesson)

        await db.executemany(
            "INSERT INTO schedule_state (uid, state) VALUES (?, ?)"
            " ON CONFLICT(uid) DO UPDATE SET state = excluded.state",
            [(key(l), l.state) for l in lessons],
        )
        await db.commit()

    return changed
