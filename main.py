import asyncio
import logging

from bot import bot, dp, on_startup, on_shutdown


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


async def main() -> None:
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    # Pending updates are dropped in on_startup via delete_webhook();
    # start_polling has no skip_updates in aiogram 3 — it silently became
    # contextual data and skipped precisely nothing.
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
