"""Per-chat bot message ID tracking for cleanup before sending new content."""
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

_user_msgs: dict[int, list[int]] = {}


def track(chat_id: int, *msg_ids: int) -> None:
    _user_msgs[chat_id] = list(msg_ids)


async def cleanup(bot: Bot, chat_id: int) -> None:
    for mid in _user_msgs.pop(chat_id, []):
        try:
            await bot.delete_message(chat_id, mid)
        except TelegramBadRequest:
            pass
