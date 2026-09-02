"""Scheduled broadcast jobs: morning summary, cancellation checks, reminders."""
import asyncio
import logging
from datetime import datetime, timedelta
from functools import partial
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import storage
from formatter import fmt_day, lesson_title
from locales import t
from msg_tracker import cleanup as _cleanup_msgs, track as _track_msgs
from scraper import Lesson, fetch_schedule

logger = logging.getLogger(__name__)

# APScheduler defaults to misfire_grace_time=1s, which means a laptop that dozed
# off for two seconds silently eats your reminder. Five minutes late beats never.
scheduler = AsyncIOScheduler(
    timezone=config.TZ,
    job_defaults={"coalesce": True, "misfire_grace_time": 300, "max_instances": 1},
)


# ── Keyboards ─────────────────────────────────────────────────────────────────

def _menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data="nav:open"),
    ]])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _fetch(week_offset: int = 0) -> list[Lesson]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(fetch_schedule, config.GROUP_ID, week_offset)
    )


async def _broadcast(
    bot: Bot,
    text_fn,
    with_menu: bool = True,
    replace_previous: bool = True,
) -> None:
    """Send text_fn(lang) to every active subscriber; deactivate on Forbidden.

    replace_previous=False keeps whatever the bot already said in the chat.
    Alerts and reminders use that: wiping the chat before every single one meant
    that two things happening at once left you with exactly one of them.
    """
    subscribers = await storage.get_active_subscribers()
    for sub in subscribers:
        chat_id = sub["chat_id"]
        lang    = sub["language"]
        try:
            if replace_previous:
                await _cleanup_msgs(bot, chat_id)
            msg = await bot.send_message(
                chat_id,
                text_fn(lang),
                reply_markup=_menu_kb(lang) if with_menu else None,
            )
            _track_msgs(chat_id, msg.message_id)
        except TelegramForbiddenError:
            logger.warning("Bot blocked by %s — deactivating", chat_id)
            await storage.deactivate(chat_id)
        except Exception as exc:
            logger.error("Failed to send to %s: %s", chat_id, exc)


# ── Jobs ──────────────────────────────────────────────────────────────────────

async def job_morning_schedule(bot: Bot) -> None:
    logger.info("Running morning schedule job")
    try:
        lessons = await _fetch(0)
        today   = config.today()

        def make_text(lang: str) -> str:
            return f"{t(lang, 'morning_greeting')}\n\n{fmt_day(lessons, today, lang)}"

        await _broadcast(bot, make_text)
        _schedule_reminders(bot, lessons)
    except Exception as exc:
        logger.error("Morning job failed: %s", exc)


async def job_check_cancellations(bot: Bot) -> None:
    logger.info("Checking for cancellations")
    try:
        lessons   = await _fetch(0)
        cancelled = await storage.find_newly_cancelled(lessons)

        for lesson in cancelled:
            def make_text(lang: str, _lesson: Lesson = lesson) -> str:
                title = escape(lesson_title(_lesson, lang))
                return (
                    f"{t(lang, 'cancelled_alert_title')}\n\n"
                    f"❌ <b>{title}</b>\n"
                    f"📅 {_lesson.date.strftime('%d.%m.%Y')}\n"
                    f"⏰ {_lesson.time_start} – {_lesson.time_end}\n"
                    f"👤 {escape(_lesson.staff)}"
                )
            # Several classes can get axed in one go — each alert must survive.
            await _broadcast(bot, make_text, replace_previous=False)
    except Exception as exc:
        logger.error("Cancellation check failed: %s", exc)


async def _send_reminder(bot: Bot, lesson: Lesson) -> None:
    def make_text(lang: str) -> str:
        lines = [
            t(lang, "reminder_title", minutes=config.REMINDER_MINUTES_BEFORE),
            f"📚 <b>{escape(lesson_title(lesson, lang))}</b>",
            f"⏰ {lesson.time_start} – {lesson.time_end}",
        ]
        if lesson.online:
            lines.append(f"🌐 <i>{t(lang, 'online_label')}</i>")
        elif lesson.room:
            loc = escape(lesson.room)
            if lesson.room_building and lesson.room_building not in ("", "None"):
                loc += f", {escape(lesson.room_building)}"
            lines.append(f"🏛 {loc}")
        if lesson.staff:
            lines.append(f"👤 {escape(lesson.staff)}")
        return "\n".join(lines)

    try:
        # Two classes at 08:30 means two reminders at 08:15. Both get to live.
        await _broadcast(bot, make_text, replace_previous=False)
    except Exception as exc:
        logger.error("Failed to send reminder: %s", exc)


def _schedule_reminders(bot: Bot, lessons: list[Lesson]) -> None:
    today = config.today()
    now   = config.now()

    for lesson in lessons:
        if lesson.date != today or lesson.is_cancelled:
            continue

        try:
            start = datetime.strptime(lesson.time_start, "%H:%M").time()
        except ValueError:
            logger.warning(
                "Lesson '%s' has unusable start time %r — no reminder for it",
                lesson.title, lesson.time_start,
            )
            continue

        lesson_dt = datetime.combine(lesson.date, start, tzinfo=config.TZ)
        remind_at = lesson_dt - timedelta(minutes=config.REMINDER_MINUTES_BEFORE)

        if remind_at <= now:
            continue

        job_id = f"reminder_{lesson.uid}"
        scheduler.add_job(
            _send_reminder,
            trigger="date",
            run_date=remind_at,
            args=[bot, lesson],
            id=job_id,
            replace_existing=True,
        )
        logger.info("Scheduled reminder: %s at %s", lesson.title, remind_at.strftime("%H:%M %Z"))


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup(bot: Bot) -> None:
    h, m = map(int, config.MORNING_NOTIFY_TIME.split(":"))

    scheduler.add_job(
        job_morning_schedule,
        trigger="cron",
        hour=h, minute=m,
        args=[bot],
        id="morning_schedule",
        # If the machine was asleep at 07:00 and woke at 09:00, the schedule is
        # still worth reading. An hour of grace, then we let it go.
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        job_check_cancellations,
        trigger="interval",
        minutes=config.CHECK_INTERVAL_MINUTES,
        args=[bot],
        id="check_cancellations",
    )
    scheduler.start()
    logger.info("Scheduler started in timezone %s", config.TIMEZONE)
