import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN      = os.environ["TELEGRAM_BOT_TOKEN"]
GROUP_ID                = os.getenv("GROUP_ID", "26R-22302-PLK-1")
MORNING_NOTIFY_TIME     = os.getenv("MORNING_NOTIFY_TIME", "07:00")
REMINDER_MINUTES_BEFORE = int(os.getenv("REMINDER_MINUTES_BEFORE", "15"))
CHECK_INTERVAL_MINUTES  = int(os.getenv("CHECK_INTERVAL_MINUTES", "20"))
DEFAULT_LANGUAGE        = os.getenv("DEFAULT_LANGUAGE", "ru")
