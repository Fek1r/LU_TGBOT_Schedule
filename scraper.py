import logging
from dataclasses import dataclass
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://lekciju-saraksts.lu.lv"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; LU-Schedule-Bot/1.0)"}


@dataclass
class Lesson:
    title: str
    title_en: str
    module_id: str
    time_start: str       # "HH:MM"
    time_end: str         # "HH:MM"
    date: date
    day: str              # "Pr", "Ot", "Tr", ...
    staff: str
    room: str
    room_building: str
    event_type: str       # "Lekcija | Lecture" etc.
    state: str            # "Live" or "Cancelled"
    online: bool

    @property
    def uid(self) -> str:
        """Unique key for this lesson — used in state storage."""
        return f"{self.date}_{self.time_start}_{self.module_id}"

    @property
    def is_cancelled(self) -> bool:
        return self.state == "Cancelled"


def fetch_schedule(group_id: str, week_offset: int = 0) -> list[Lesson]:
    """
    Fetch and parse lessons for the given group.
    week_offset: 0 = current week, 1 = next, -1 = previous.
    Raises RuntimeError on network errors, ValueError if group not found.
    """
    url    = f"{BASE_URL}/grupa/{group_id}/nedela"
    params = {"nedela": week_offset} if week_offset != 0 else {}

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Network error fetching schedule: {exc}") from exc

    soup = BeautifulSoup(resp.text, "html.parser")

    # Detect 404 / wrong group
    if not soup.select(".group-heading") and not soup.select(".ev-block"):
        raise ValueError(f"Group '{group_id}' not found (page returned 404 or is empty)")

    lessons: list[Lesson] = []

    for block in soup.select(".ev-block"):
        attrs     = block.attrs
        date_str  = attrs.get("data-date", "")

        try:
            lesson_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            logger.warning("Could not parse date '%s', skipping block", date_str)
            continue

        title    = attrs.get("data-title")    or attrs.get("data-module")    or "—"
        title_en = attrs.get("data-title-en") or attrs.get("data-module-en") or title

        lessons.append(Lesson(
            title         = title,
            title_en      = title_en,
            module_id     = attrs.get("data-module-id", ""),
            time_start    = attrs.get("data-time", ""),
            time_end      = attrs.get("data-time2", ""),
            date          = lesson_date,
            day           = attrs.get("data-day", ""),
            staff         = attrs.get("data-staff", ""),
            room          = attrs.get("data-room", ""),
            room_building = attrs.get("data-room-building", ""),
            event_type    = attrs.get("data-event-type", ""),
            state         = attrs.get("data-state", "Live"),
            online        = attrs.get("data-online", "") == "1",
        ))

    return sorted(lessons, key=lambda l: (l.date, l.time_start))
