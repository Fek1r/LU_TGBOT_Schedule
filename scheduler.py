"""Scheduled broadcast jobs: morning summary, cancellation checks, reminders."""
import asyncio
import logging
from datetime import date, datetime, timedelta
from functools import partial
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import storage
from formatter import fmt_day, fmt_week, fmt_lesson, lesson_title
from locales import t
from scraper import Lesson, fetch_schedule

logger    = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


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


async def _broadcast(bot: Bot, text_fn, with_menu: bool = True) -> None:
    """Send text_fn(lang) to every active subscriber; deactivate on Forbidden."""
    subscribers = await storage.get_active_subscribers()
    for sub in subscribers:
        chat_id = sub["chat_id"]
        lang    = sub["language"]
        try:
            await bot.send_message(
                chat_id,
                text_fn(lang),
                reply_markup=_menu_kb(lang) if with_menu else None,
            )
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
        today   = date.today()

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
                title    = escape(lesson_title(_lesson, lang))
                day_name = fmt_day([_lesson], _lesson.date, lang).split("\n")[0]
                return (
                    f"{t(lang, 'cancelled_alert_title')}\n\n"
                    f"❌ <b>{title}</b>\n"
                    f"📅 {_lesson.date.strftime('%d.%m.%Y')}\n"
                    f"⏰ {_lesson.time_start} – {_lesson.time_end}\n"
                    f"👤 {escape(_lesson.staff)}"
                )
            await _broadcast(bot, make_text)
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
            lines.append(f"🏛 {escape(lesson.room)}")
        if lesson.staff:
            lines.append(f"👤 {escape(lesson.staff)}")
        return "\n".join(lines)

    try:
        await _broadcast(bot, make_text)
    except Exception as exc:
        logger.error("Failed to send reminder: %s", exc)


def _schedule_reminders(bot: Bot, lessons: list[Lesson]) -> None:
    today = date.today()
    now   = datetime.now()

    for lesson in lessons:
        if lesson.date != today or lesson.is_cancelled:
            continue

        lesson_dt = datetime.combine(
            lesson.date,
            datetime.strptime(lesson.time_start, "%H:%M").time(),
        )
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
        logger.info("Scheduled reminder: %s at %s", lesson.title, remind_at.strftime("%H:%M"))


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup(bot: Bot) -> None:
    h, m = map(int, config.MORNING_NOTIFY_TIME.split(":"))

    scheduler.add_job(
        job_morning_schedule,
        trigger="cron",
        hour=h, minute=m,
        args=[bot],
        id="morning_schedule",
    )
    scheduler.add_job(
        job_check_cancellations,
        trigger="interval",
        minutes=config.CHECK_INTERVAL_MINUTES,
        args=[bot],
        id="check_cancellations",
    )
    scheduler.start()
