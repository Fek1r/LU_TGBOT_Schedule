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
    BotCommand, BotCommandScopeChat, BotCommandScopeDefault,
    InlineKeyboardButton, InlineKeyboardMarkup,
    LinkPreviewOptions, ReplyKeyboardRemove,
)

import config
import storage
import scheduler as sched
from formatter import fmt_day, fmt_week
from locales import LOCALES, t
from msg_tracker import cleanup as _cleanup_msgs, track as _track_msgs
from scraper import fetch_schedule, Lesson

logger = logging.getLogger(__name__)

# The disclaimer name-drops lekciju-saraksts.lu.lv; Telegram would happily
# staple a preview card to it. It would not.
_NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

bot = Bot(
    token=config.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


# ── Command menu ──────────────────────────────────────────────────────────────

# Order matters — this is the order Telegram shows them in the ☰ menu.
_COMMANDS = ("start", "language", "about", "stop")


def _command_list(lang: str) -> list[BotCommand]:
    descriptions = LOCALES.get(lang, LOCALES["ru"])["commands"]
    return [BotCommand(command=c, description=descriptions[c]) for c in _COMMANDS]


async def _apply_commands(chat_id: int, lang: str) -> None:
    """Set the ☰ menu for one chat in the language they picked in the bot.

    Telegram's own language_code targeting follows the user's *client* language,
    which has no idea our language picker exists. Per-chat scope does.
    """
    try:
        await bot.set_my_commands(
            _command_list(lang), scope=BotCommandScopeChat(chat_id=chat_id)
        )
    except TelegramBadRequest as exc:
        logger.warning("Could not set commands for %s: %s", chat_id, exc)


async def _apply_default_commands() -> None:
    """Baseline menu for anyone who has not picked a language yet."""
    await bot.set_my_commands(
        _command_list(config.DEFAULT_LANGUAGE), scope=BotCommandScopeDefault()
    )
    for lang in LOCALES:
        await bot.set_my_commands(
            _command_list(lang), scope=BotCommandScopeDefault(), language_code=lang
        )


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
        [
            InlineKeyboardButton(text=t(lang, "btn_about"), callback_data="nav:about"),
        ],
    ])


def back_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="nav:back"),
    ]])


def menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data="nav:open"),
    ]])


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский",  callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English",  callback_data="lang:en"),
        InlineKeyboardButton(text="🇱🇻 Latviešu", callback_data="lang:lv"),
    ]])


# ── Message tracking helpers ──────────────────────────────────────────────────

async def _cleanup(chat_id: int) -> None:
    await _cleanup_msgs(bot, chat_id)


def _track(chat_id: int, *msg_ids: int) -> None:
    _track_msgs(chat_id, *msg_ids)


# ── Fetch / misc helpers ──────────────────────────────────────────────────────

async def _fetch(week_offset: int = 0) -> list[Lesson]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(fetch_schedule, config.GROUP_ID, week_offset)
    )


def _offset_for(target: date) -> int:
    today  = config.today()
    monday = today - timedelta(days=today.weekday())
    if target >= monday + timedelta(days=7):
        return 1
    if target < monday:
        return -1
    return 0


async def _lang(chat_id: int) -> str:
    sub = await storage.get_subscriber(chat_id)
    return sub["language"] if sub else config.DEFAULT_LANGUAGE


async def _send_home(chat_id: int, lang: str) -> None:
    await _cleanup(chat_id)
    msg = await bot.send_message(
        chat_id,
        t(lang, "welcome", group=config.GROUP_ID),
        reply_markup=nav_kb(lang),
    )
    _track(chat_id, msg.message_id)


# ── /start ────────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    stub = await message.answer(".", reply_markup=ReplyKeyboardRemove())
    try:
        await stub.delete()
    except TelegramBadRequest:
        pass

    sub = await storage.get_subscriber(message.chat.id)
    if sub is None:
        msg = await message.answer(
            t(config.DEFAULT_LANGUAGE, "choose_language"),
            reply_markup=lang_kb(),
        )
        _track(message.chat.id, msg.message_id)
    else:
        await storage.upsert_subscriber(message.chat.id, sub["language"])
        await _apply_commands(message.chat.id, sub["language"])
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
    await _cleanup(message.chat.id)
    msg = await message.answer(t(lang, "choose_language"), reply_markup=lang_kb())
    _track(message.chat.id, msg.message_id)


@dp.message(Command("about"))
async def cmd_about(message: types.Message) -> None:
    lang = await _lang(message.chat.id)
    await _cleanup(message.chat.id)
    msg = await message.answer(
        t(lang, "about"),
        reply_markup=back_kb(lang),
        link_preview_options=_NO_PREVIEW,
    )
    _track(message.chat.id, msg.message_id)


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

    await _apply_commands(chat_id, chosen)

    await callback.answer()
    await _cleanup(chat_id)
    msg = await bot.send_message(chat_id, t(chosen, "language_set"))
    # immediately replace with home menu
    await bot.delete_message(chat_id, msg.message_id)
    await _send_home(chat_id, chosen)


# ── Navigation callbacks ──────────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("nav:"))
async def cb_nav(callback: types.CallbackQuery) -> None:
    action  = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    lang    = await _lang(chat_id)

    await callback.answer()

    # ── Back / open menu ──────────────────────────────────────────────────────
    if action in ("back", "open"):
        await _send_home(chat_id, lang)
        return

    # ── Language picker ───────────────────────────────────────────────────────
    if action == "language":
        await _cleanup(chat_id)
        msg = await bot.send_message(
            chat_id, t(lang, "choose_language"), reply_markup=lang_kb()
        )
        _track(chat_id, msg.message_id)
        return

    # ── About / disclaimer ────────────────────────────────────────────────────
    if action == "about":
        await _cleanup(chat_id)
        msg = await bot.send_message(
            chat_id,
            t(lang, "about"),
            reply_markup=back_kb(lang),
            link_preview_options=_NO_PREVIEW,
        )
        _track(chat_id, msg.message_id)
        return

    # ── Today / Tomorrow ─────────────────────────────────────────────────────
    if action in ("today", "tomorrow"):
        try:
            if action == "today":
                lessons = await _fetch(0)
                target  = config.today()
            else:
                target  = config.today() + timedelta(days=1)
                lessons = await _fetch(_offset_for(target))
            text = fmt_day(lessons, target, lang)
        except Exception as exc:
            logger.error("nav:%s failed: %s", action, exc)
            text = t(lang, "error")

        await _cleanup(chat_id)
        msg = await bot.send_message(chat_id, text, reply_markup=back_kb(lang))
        _track(chat_id, msg.message_id)
        return

    # ── Week / Next week ──────────────────────────────────────────────────────
    if action in ("week", "nextweek"):
        offset = 0 if action == "week" else 1
        try:
            lessons = await _fetch(offset)
        except Exception as exc:
            logger.error("nav:%s failed: %s", action, exc)
            await _cleanup(chat_id)
            msg = await bot.send_message(chat_id, t(lang, "error"), reply_markup=back_kb(lang))
            _track(chat_id, msg.message_id)
            return

        await _cleanup(chat_id)

        if not lessons:
            msg = await bot.send_message(
                chat_id, t(lang, "no_lessons_week"), reply_markup=back_kb(lang)
            )
            _track(chat_id, msg.message_id)
            return

        blocks   = fmt_week(lessons, lang)
        msg_ids  = []
        for i, block in enumerate(blocks):
            is_last = (i == len(blocks) - 1)
            msg = await bot.send_message(
                chat_id,
                block,
                reply_markup=back_kb(lang) if is_last else None,
            )
            msg_ids.append(msg.message_id)
        _track(chat_id, *msg_ids)
        return


# ── Startup / shutdown ────────────────────────────────────────────────────────

async def on_startup() -> None:
    await storage.init_db()
    await _apply_default_commands()
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
