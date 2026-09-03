"""Bot handlers and startup/shutdown hooks."""
import asyncio
import logging
from datetime import date, timedelta
from html import escape

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
import fetcher
import groups
import roster
import storage
import scheduler as sched
from formatter import fmt_day, fmt_week
from locales import LOCALES, t
from msg_tracker import cleanup as _cleanup_msgs, track as _track_msgs
from scraper import Lesson

logger = logging.getLogger(__name__)

# The disclaimer name-drops lekciju-saraksts.lu.lv; Telegram would happily
# staple a preview card to it. It would not.
_NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

# Chats whose next message is a search query, and what they are searching for
# ("group" or "me"). Deliberately in memory: losing it on restart costs the
# user one extra tap.
_awaiting: dict[int, str] = {}

bot = Bot(
    token=config.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


# ── Command menu ──────────────────────────────────────────────────────────────

# Order matters — this is the order Telegram shows them in the ☰ menu.
_COMMANDS = ("start", "me", "group", "language", "about", "stop")


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
            InlineKeyboardButton(text=t(lang, "btn_me"),       callback_data="nav:me"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_group"),    callback_data="nav:group"),
        ],
        [
            InlineKeyboardButton(text="🌐 Язык / Language / Valoda", callback_data="nav:language"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_about"),    callback_data="nav:about"),
        ],
    ])


def back_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="nav:back"),
    ]])


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский",  callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English",  callback_data="lang:en"),
        InlineKeyboardButton(text="🇱🇻 Latviešu", callback_data="lang:lv"),
    ]])


def groups_kb(lang: str, found: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=groups.short_name(gid), callback_data=f"group:{gid}")]
        for gid, _ in found
    ]
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="nav:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def roster_kb(lang: str, found: list, current: str | None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=roster.describe(s),
                              callback_data=f"roster:{roster.make_ref(key, s['n'])}")]
        for key, s in found
    ]
    if current:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_me_off"),
                                          callback_data="roster:off")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="nav:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Message tracking helpers ──────────────────────────────────────────────────

async def _cleanup(chat_id: int) -> None:
    await _cleanup_msgs(bot, chat_id)


def _track(chat_id: int, *msg_ids: int) -> None:
    _track_msgs(chat_id, *msg_ids)


async def _replace(chat_id: int, text: str, markup=None, preview: bool = True) -> None:
    """Wipe what the bot said before and say this instead."""
    await _cleanup(chat_id)
    msg = await bot.send_message(
        chat_id, text, reply_markup=markup,
        link_preview_options=None if preview else _NO_PREVIEW,
    )
    _track(chat_id, msg.message_id)


# ── Fetch / misc helpers ──────────────────────────────────────────────────────

async def _fetch(group_id: str, week_offset: int = 0) -> list[Lesson]:
    return await fetcher.fetch(group_id, week_offset)


def _offset_for(target: date) -> int:
    today  = config.today()
    monday = today - timedelta(days=today.weekday())
    if target >= monday + timedelta(days=7):
        return 1
    if target < monday:
        return -1
    return 0


async def _sub(chat_id: int) -> dict:
    """Subscriber row, or sensible defaults for someone who never pressed /start."""
    sub = await storage.get_subscriber(chat_id)
    return sub or {"language": config.DEFAULT_LANGUAGE, "group_id": config.GROUP_ID}


def _student_of(sub: dict) -> dict | None:
    return roster.student_for(sub)


def _personalise(sub: dict, lessons: list[Lesson]) -> list[Lesson]:
    return roster.personalise(sub, lessons, config.SEMESTER_START)


def _gap_note(sub: dict, lessons: list[Lesson], lang: str, for_date: date) -> str:
    """Warn when the distribution list has a class the website is missing."""
    student = _student_of(sub)
    if not student:
        return ""
    gaps = roster.missing_from_site(student, lessons, config.SEMESTER_START, for_date)
    if not gaps:
        return ""
    lines = [
        f"• {g['time']} {g['module']} "
        + (f"гр. {g['label']}" if g["label"] else "")
        + (f", {g['room']}." if g["room"] else "")
        for g in gaps
    ]
    return "\n\n" + t(lang, "me_gap") + "\n" + "\n".join(lines)


async def _send_home(chat_id: int, lang: str, group_id: str) -> None:
    await _replace(
        chat_id,
        t(lang, "welcome", group=escape(groups.short_name(group_id))),
        nav_kb(lang),
    )


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
        await _replace(
            message.chat.id,
            t(config.DEFAULT_LANGUAGE, "choose_language"),
            lang_kb(),
        )
    else:
        await storage.upsert_subscriber(message.chat.id, sub["language"])
        await _apply_commands(message.chat.id, sub["language"])
        await _send_home(message.chat.id, sub["language"], sub["group_id"])


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


# ── /language, /group, /about, /help ──────────────────────────────────────────

@dp.message(Command("language"))
async def cmd_language(message: types.Message) -> None:
    sub = await _sub(message.chat.id)
    await _replace(message.chat.id, t(sub["language"], "choose_language"), lang_kb())


@dp.message(Command("group"))
async def cmd_group(message: types.Message) -> None:
    sub = await _sub(message.chat.id)
    await _prompt_for_group(message.chat.id, sub["language"], sub["group_id"])


@dp.message(Command("about"))
async def cmd_about(message: types.Message) -> None:
    sub = await _sub(message.chat.id)
    await _replace(message.chat.id, t(sub["language"], "about"), back_kb(sub["language"]),
                   preview=False)


@dp.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    sub = await _sub(message.chat.id)
    await _send_home(message.chat.id, sub["language"], sub["group_id"])


# ── Group picking ─────────────────────────────────────────────────────────────

async def _prompt_for_group(chat_id: int, lang: str, group_id: str) -> None:
    _awaiting[chat_id] = "group"
    await _replace(
        chat_id,
        t(lang, "group_prompt", group=escape(groups.short_name(group_id))),
        back_kb(lang),
    )


async def _prompt_for_me(chat_id: int, sub: dict) -> None:
    lang = sub["language"]
    _awaiting[chat_id] = "me"
    student = _student_of(sub)
    who = f"<b>{escape(roster.describe(student))}</b>" if student else t(lang, "me_off")
    await _replace(chat_id, t(lang, "me_prompt", who=who), back_kb(lang))


@dp.message(Command("me"))
async def cmd_me(message: types.Message) -> None:
    await _prompt_for_me(message.chat.id, await _sub(message.chat.id))


@dp.callback_query(F.data.startswith("roster:"))
async def cb_roster(callback: types.CallbackQuery) -> None:
    ref     = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    sub     = await _sub(chat_id)

    await callback.answer()
    _awaiting.pop(chat_id, None)

    if await storage.get_subscriber(chat_id) is None:
        await storage.upsert_subscriber(chat_id, sub["language"])
    await storage.set_roster(chat_id, None if ref == "off" else ref)
    logger.info("Chat %s pinned to roster %s", chat_id, ref)

    await _send_home(chat_id, sub["language"], sub["group_id"])


@dp.callback_query(F.data.startswith("group:"))
async def cb_group(callback: types.CallbackQuery) -> None:
    chosen  = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    sub     = await _sub(chat_id)

    await callback.answer()
    _awaiting.pop(chat_id, None)

    if await storage.get_subscriber(chat_id) is None:
        await storage.upsert_subscriber(chat_id, sub["language"])
    await storage.set_group(chat_id, chosen)
    logger.info("Chat %s switched to group %s", chat_id, chosen)

    await _send_home(chat_id, sub["language"], chosen)


# ── Any other text ────────────────────────────────────────────────────────────

@dp.message(F.text)
async def on_text(message: types.Message) -> None:
    """Either a group search, or a gentle nudge back towards the buttons."""
    chat_id = message.chat.id
    sub     = await _sub(chat_id)
    lang    = sub["language"]

    mode = _awaiting.get(chat_id)
    if mode is None:
        await message.answer(t(lang, "hint"))
        return

    query = message.text.strip()
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if mode == "me":
        found = roster.search(query)
        if not found:
            await _replace(chat_id, t(lang, "me_none", query=escape(query)), back_kb(lang))
            return
        student = _student_of(sub)
        who = f"<b>{escape(roster.describe(student))}</b>" if student else t(lang, "me_off")
        await _replace(chat_id, t(lang, "me_prompt", who=who),
                       roster_kb(lang, found, sub.get("roster_ref")))
        return

    found = await asyncio.to_thread(groups.search, query)
    if not found:
        await _replace(chat_id, t(lang, "group_none", query=escape(query)), back_kb(lang))
        return

    await _replace(chat_id, t(lang, "group_prompt", group=escape(groups.short_name(sub["group_id"]))),
                   groups_kb(lang, found))


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

    await callback.answer()
    await _apply_commands(chat_id, chosen)
    await _send_home(chat_id, chosen, (sub or {}).get("group_id") or config.GROUP_ID)


# ── Navigation callbacks ──────────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("nav:"))
async def cb_nav(callback: types.CallbackQuery) -> None:
    action   = callback.data.split(":", 1)[1]
    chat_id  = callback.message.chat.id
    sub      = await _sub(chat_id)
    lang     = sub["language"]
    group_id = sub["group_id"]

    await callback.answer()
    if action not in ("group", "me"):
        _awaiting.pop(chat_id, None)

    if action in ("back", "open"):
        await _send_home(chat_id, lang, group_id)
        return

    if action == "group":
        await _prompt_for_group(chat_id, lang, group_id)
        return

    if action == "me":
        await _prompt_for_me(chat_id, sub)
        return

    if action == "language":
        await _replace(chat_id, t(lang, "choose_language"), lang_kb())
        return

    if action == "about":
        await _replace(chat_id, t(lang, "about"), back_kb(lang), preview=False)
        return

    if action in ("today", "tomorrow"):
        try:
            if action == "today":
                target  = config.today()
                lessons = await _fetch(group_id, 0)
            else:
                target  = config.today() + timedelta(days=1)
                lessons = await _fetch(group_id, _offset_for(target))
            text = fmt_day(_personalise(sub, lessons), target, lang) \
                 + _gap_note(sub, lessons, lang, target)
        except Exception as exc:
            logger.error("nav:%s failed for %s: %s", action, group_id, exc)
            text = t(lang, "error")

        await _replace(chat_id, text, back_kb(lang))
        return

    if action in ("week", "nextweek"):
        offset = 0 if action == "week" else 1
        try:
            lessons = await _fetch(group_id, offset)
        except Exception as exc:
            logger.error("nav:%s failed for %s: %s", action, group_id, exc)
            await _replace(chat_id, t(lang, "error"), back_kb(lang))
            return

        lessons = _personalise(sub, lessons)
        await _cleanup(chat_id)

        if not lessons:
            await _replace(chat_id, t(lang, "no_lessons_week"), back_kb(lang))
            return

        blocks  = fmt_week(lessons, lang)
        msg_ids = []
        for i, block in enumerate(blocks):
            is_last = (i == len(blocks) - 1)
            msg = await bot.send_message(
                chat_id, block, reply_markup=back_kb(lang) if is_last else None
            )
            msg_ids.append(msg.message_id)
        _track(chat_id, *msg_ids)
        return


# ── Startup / shutdown ────────────────────────────────────────────────────────

async def on_startup() -> None:
    await storage.init_db()
    roster.load()
    await bot.delete_webhook(drop_pending_updates=True)
    await _apply_default_commands()
    await asyncio.to_thread(groups.refresh)
    sched.setup(bot)

    for group_id in await storage.active_group_ids():
        try:
            lessons = await _fetch(group_id, 0)
            await storage.find_newly_cancelled(group_id, lessons)
            sched.schedule_reminders(bot, group_id, lessons)
        except Exception as exc:
            logger.error("Startup fetch failed for %s: %s", group_id, exc)

    logger.info(
        "Bot started. Morning notify at %s, checks every %d min.",
        config.MORNING_NOTIFY_TIME,
        config.CHECK_INTERVAL_MINUTES,
    )


async def on_shutdown() -> None:
    sched.scheduler.shutdown(wait=False)
    await bot.session.close()
