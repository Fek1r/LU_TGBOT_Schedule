import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TELEGRAM_BOT_TOKEN:
    # A bare KeyError traceback is a poor welcome on a fresh server.
    raise SystemExit(
        "TELEGRAM_BOT_TOKEN is not set.\n"
        "  local  : cp .env.example .env and fill in the token from @BotFather\n"
        "  docker : docker compose reads .env from the project directory"
    )
GROUP_ID                = os.getenv("GROUP_ID", "26R-22302-PLK-1")
MORNING_NOTIFY_TIME     = os.getenv("MORNING_NOTIFY_TIME", "07:00")
REMINDER_MINUTES_BEFORE = int(os.getenv("REMINDER_MINUTES_BEFORE", "15"))
CHECK_INTERVAL_MINUTES  = int(os.getenv("CHECK_INTERVAL_MINUTES", "20"))
DEFAULT_LANGUAGE        = os.getenv("DEFAULT_LANGUAGE", "ru")

# Touched on every cancellation round so a container healthcheck can tell a
# wedged process from a working one. Empty disables it.
HEARTBEAT_FILE          = os.getenv("HEARTBEAT_FILE", "")

# lekciju-saraksts.lu.lv always speaks Riga wall-clock time. The server hosting
# the bot is under no obligation to agree (Railway happily runs on UTC), so
# every "now" and "today" in this bot goes through here instead of asking the OS.
SEMESTER_START = date.fromisoformat(os.getenv("SEMESTER_START", "2026-08-31"))

TIMEZONE = os.getenv("TIMEZONE", "Europe/Riga")
TZ       = ZoneInfo(TIMEZONE)


def now() -> datetime:
    """Timezone-aware current moment, in the university's timezone."""
    return datetime.now(TZ)


def today() -> date:
    """Today as the university sees it — not as the server does."""
    return now().date()
