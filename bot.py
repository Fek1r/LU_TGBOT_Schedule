"""Bot handlers and startup/shutdown hooks."""
import asyncio
import logging
from datetime import date, timedelta
from functools import partial

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)

import config
import storage
import scheduler as sched
from formatter import fmt_day, fmt_week
from locales import t
from scraper import fetch_schedule, Lesson

logger = logging.getLogger(__name__)

bot = Bot(
    token=config.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

# Tracks the current nav message per chat (ephemeral — lost on restart)
_home_msg: dict[int, int] = {}


# ── Keyboards ─────────────────────────────────────────────────────────────────

def nav_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "btn_today"),    callback_data="nav:today"),
            InlineKeyboardButton(text=t(lang, "btn_tomorrow"), callback_data="nav:tomorrow"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_week"),     callback_data="nav:week"),
            InlineKeyboardButton(text=t(lang, "btn_nextweek"), callback_data="nav:nextweek"),
        ],
        [
            InlineKeyboardButton(text="🌐 Язык / Language / Valoda", callback_data="nav:language"),
        ],
    ])


def back_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="nav:back"),
    ]])


def menu_kb(lang: str) -> InlineKeyboardMarkup:
    """Used on broadcast messages so user can open the nav from there."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data="nav:open"),
    ]])


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский",  callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English",  callback_data="lang:en"),
        InlineKeyboardButton(text="🇱🇻 Latviešu", callback_data="lang:lv"),
    ]])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _fetch(week_offset: int = 0) -> list[Lesson]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(fetch_schedule, config.GROUP_ID, week_offset)
    )


def _offset_for(target: date) -> int:
    monday = date.today() - timedelta(days=date.today().weekday())
    if target >= monday + timedelta(days=7):
        return 1
    if target < monday:
        return -1
    return 0


async def _lang(chat_id: int) -> str:
    sub = await storage.get_subscriber(chat_id)
    return sub["language"] if sub else config.DEFAULT_LANGUAGE


async def _send_home(chat_id: int, lang: str) -> None:
    """Send a fresh nav menu message and track its ID."""
    msg = await bot.send_message(
        chat_id,
        t(lang, "welcome", group=config.GROUP_ID),
        reply_markup=nav_kb(lang),
    )
    _home_msg[chat_id] = msg.message_id


async def _edit_to_home(callback: types.CallbackQuery, lang: str) -> None:
    """Edit the current callback message back to the nav menu."""
    try:
        await callback.message.edit_text(
            t(lang, "welcome", group=config.GROUP_ID),
            reply_markup=nav_kb(lang),
        )
        _home_msg[callback.message.chat.id] = callback.message.message_id
    except TelegramBadRequest:
        # Message was deleted or can't be edited — send a new one
        await _send_home(callback.message.chat.id, lang)


# ── /start ────────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    # Send invisible message just to strip the old Reply Keyboard, then delete it
    stub = await message.answer(".", reply_markup=ReplyKeyboardRemove())
    try:
        await stub.delete()
    except TelegramBadRequest:
        pass

    sub = await storage.get_subscriber(message.chat.id)
    if sub is None:
        await message.answer(
            t(config.DEFAULT_LANGUAGE, "choose_language"),
            reply_markup=lang_kb(),
        )
    else:
        await storage.upsert_subscriber(message.chat.id, sub["language"])
        await _send_home(message.chat.id, sub["language"])


# ── /stop ─────────────────────────────────────────────────────────────────────

@dp.message(Command("stop"))
async def cmd_stop(message: types.Message) -> None:
    sub = await storage.get_subscriber(message.chat.id)
    lang = sub["language"] if sub else config.DEFAULT_LANGUAGE
    if not sub or not sub["is_active"]:
        await message.answer(t(lang, "not_subscribed"))
        return
    await storage.deactivate(message.chat.id)
    await message.answer(t(lang, "unsubscribed"))


# ── /language, /help ──────────────────────────────────────────────────────────

@dp.message(Command("language"))
async def cmd_language(message: types.Message) -> None:
    lang = await _lang(message.chat.id)
    await message.answer(t(lang, "choose_language"), reply_markup=lang_kb())


@dp.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    lang = await _lang(message.chat.id)
    await _send_home(message.chat.id, lang)


# ── Language picker callback ──────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("lang:"))
async def cb_language(callback: types.CallbackQuery) -> None:
    chosen  = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id

    sub = await storage.get_subscriber(chat_id)
    if sub is None:
        await storage.upsert_subscriber(chat_id, chosen)
    else:
        await storage.set_language(chat_id, chosen)
        if not sub["is_active"]:
            await storage.upsert_subscriber(chat_id, chosen)

    await callback.message.edit_text(t(chosen, "language_set"))
    await _send_home(chat_id, chosen)
    await callback.answer()


# ── Navigation callbacks ──────────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("nav:"))
async def cb_nav(callback: types.CallbackQuery) -> None:
    action  = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    lang    = await _lang(chat_id)

    # ── Back / open menu ──────────────────────────────────────────────────────
    if action in ("back", "open"):
        await _edit_to_home(callback, lang)
        await callback.answer()
        return

    # ── Language picker ───────────────────────────────────────────────────────
    if action == "language":
        try:
            await callback.message.edit_text(
                t(lang, "choose_language"), reply_markup=lang_kb()
            )
        except TelegramBadRequest:
            pass
        await callback.answer()
        return

    # ── Today / Tomorrow (edit in place) ─────────────────────────────────────
    if action in ("today", "tomorrow"):
        await callback.answer()
        try:
            if action == "today":
                lessons = await _fetch(0)
                target  = date.today()
            else:
                target  = date.today() + timedelta(days=1)
                lessons = await _fetch(_offset_for(target))
            text = fmt_day(lessons, target, lang)
            try:
                await callback.message.edit_text(text, reply_markup=back_kb(lang))
                _home_msg[chat_id] = callback.message.message_id
            except TelegramBadRequest:
                msg = await bot.send_message(chat_id, text, reply_markup=back_kb(lang))
                _home_msg[chat_id] = msg.message_id
        except Exception as exc:
            logger.error("nav:%s failed: %s", action, exc)
            try:
                await callback.message.edit_text(t(lang, "error"), reply_markup=back_kb(lang))
            except TelegramBadRequest:
                pass
        return

    # ── Week / Next week (delete + send day blocks) ───────────────────────────
    if action in ("week", "nextweek"):
        await callback.answer()
        offset = 0 if action == "week" else 1
        try:
            lessons = await _fetch(offset)
            if not lessons:
                try:
                    await callback.message.edit_text(
                        t(lang, "no_lessons_week"), reply_markup=back_kb(lang)
                    )
                    _home_msg[chat_id] = callback.message.message_id
                except TelegramBadRequest:
                    pass
                return

            # Delete current nav message, send day blocks, back button on last
            try:
                await callback.message.delete()
            except TelegramBadRequest:
                pass

            blocks = fmt_week(lessons, lang)
            last_msg = None
            for i, block in enumerate(blocks):
                is_last = (i == len(blocks) - 1)
                last_msg = await bot.send_message(
                    chat_id,
                    block,
                    reply_markup=back_kb(lang) if is_last else None,
                )
            if last_msg:
                _home_msg[chat_id] = last_msg.message_id

        except Exception as exc:
            logger.error("nav:%s failed: %s", action, exc)
            try:
                msg = await bot.send_message(chat_id, t(lang, "error"), reply_markup=back_kb(lang))
                _home_msg[chat_id] = msg.message_id
            except Exception:
                pass
        return

    await callback.answer()


# ── Startup / shutdown ────────────────────────────────────────────────────────

async def on_startup() -> None:
    await storage.init_db()
    sched.setup(bot)

    try:
        lessons = await _fetch(0)
        await storage.find_newly_cancelled(lessons)
        sched._schedule_reminders(bot, lessons)
    except Exception as exc:
        logger.error("Startup fetch failed: %s", exc)

    logger.info(
        "Bot started. Morning notify at %s, checks every %d min.",
        config.MORNING_NOTIFY_TIME,
        config.CHECK_INTERVAL_MINUTES,
    )


async def on_shutdown() -> None:
    sched.scheduler.shutdown(wait=False)
    await bot.session.close()
