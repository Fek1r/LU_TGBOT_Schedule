import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN      = os.environ["TELEGRAM_BOT_TOKEN"]
GROUP_ID                = os.getenv("GROUP_ID", "26R-22302-PLK-1")
MORNING_NOTIFY_TIME     = os.getenv("MORNING_NOTIFY_TIME", "07:00")
REMINDER_MINUTES_BEFORE = int(os.getenv("REMINDER_MINUTES_BEFORE", "15"))
CHECK_INTERVAL_MINUTES  = int(os.getenv("CHECK_INTERVAL_MINUTES", "20"))
DEFAULT_LANGUAGE        = os.getenv("DEFAULT_LANGUAGE", "ru")

# lekciju-saraksts.lu.lv always speaks Riga wall-clock time. The server hosting
# the bot is under no obligation to agree (Railway happily runs on UTC), so
# every "now" and "today" in this bot goes through here instead of asking the OS.
TIMEZONE = os.getenv("TIMEZONE", "Europe/Riga")
TZ       = ZoneInfo(TIMEZONE)


def now() -> datetime:
    """Timezone-aware current moment, in the university's timezone."""
    return datetime.now(TZ)


def today() -> date:
    """Today as the university sees it — not as the server does."""
    return now().date()
