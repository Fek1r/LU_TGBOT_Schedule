"""Per-chat bot message ID tracking for cleanup before sending new content."""
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

_user_msgs: dict[int, list[int]] = {}


def track(chat_id: int, *msg_ids: int) -> None:
    """Remember bot messages so they can be cleaned up later.

    Appends — it deliberately does NOT replace. The old version overwrote the
    list, so two messages sent seconds apart forgot about each other and the
    second one cheerfully deleted the first. Great for tidiness, terrible for
    actually reading your reminders.
    """
    _user_msgs.setdefault(chat_id, []).extend(msg_ids)


async def cleanup(bot: Bot, chat_id: int) -> None:
    for mid in _user_msgs.pop(chat_id, []):
        try:
            await bot.delete_message(chat_id, mid)
        except TelegramBadRequest:
            pass
