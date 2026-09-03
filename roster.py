"""Who sits in which small group, and when.

The university publishes two PDFs per year group: one lists every student with
their subgroup for each subject, the other says when each subgroup meets. The
website knows neither — it shows all parallel sessions of the whole year and
leaves you to guess which one is yours. tools/build_roster.py folds the two
PDFs into data/*.json; this module reads that and answers the only question
that matters: is this particular lesson mine?
"""
import hashlib
import json
import logging
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

# Website dates are authoritative; its data-day uses 'Ot'/'Tr'/'Ce' while the
# PDFs use 'O'/'T'/'C', so we never compare those strings — we derive the day
# from the date and speak the PDF's dialect.
_DAY_BY_WEEKDAY = ["Pr", "O", "T", "C", "Pk", "Se", "Sv"]
_FIRST_NUMBER   = re.compile(r"\d+")

_rosters: dict[str, dict] = {}


# ── Loading ───────────────────────────────────────────────────────────────────

def load() -> dict[str, dict]:
    """Read every roster JSON in data/. Called once at startup."""
    global _rosters
    found = {}
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            found[path.stem] = data
            logger.info("Roster %s: %d students", path.stem, len(data["students"]))
        except Exception as exc:
            logger.error("Could not read roster %s: %s", path, exc)
    _rosters = found
    return _rosters


# ── Finding a person ──────────────────────────────────────────────────────────

def _fold(text: str) -> str:
    """'Krasikovs' and 'Kraņičs' both lose their diacritics here."""
    stripped = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in stripped if not unicodedata.combining(c))


# Must match tools/build_roster.py — the rosters store hashed name tokens so
# the repository never carries a class list in plain text.
SALT = "lu-schedule-bot/roster/v1"


def _hash(token: str) -> str:
    return hashlib.sha256((SALT + token).encode()).hexdigest()[:16]


def search(query: str, limit: int = 10) -> list[tuple[str, dict]]:
    """Every term of the query must be one of the person's name tokens.

    Matching happens on hashes, so a surname types the same as ever while the
    roster file itself holds no names.
    """
    wanted = {_hash(_fold(t)) for t in query.split() if t}
    if not wanted:
        return []
    hits = []
    for key, data in _rosters.items():
        for student in data["students"]:
            if wanted <= set(student.get("h", [])):
                hits.append((key, student))
    return hits[:limit]


def describe(student: dict) -> str:
    """A label the person recognises as themselves, without naming them."""
    # Numbers first and in numeric order, letter groups after: 4, 4a, 12, E.
    labels = sorted({e["label"] for e in student["entries"] if e["label"]},
                    key=lambda x: (not x[0].isdigit(), int(re.match(r"\d*", x).group() or 0), x))
    tail = ", ".join(labels) if labels else "—"
    return f"№{student['n']} · pl. {student['flow']} · {tail}"


def get(roster_key: str, number: int) -> dict | None:
    data = _rosters.get(roster_key)
    if not data:
        return None
    return next((s for s in data["students"] if s["n"] == number), None)


def parse_ref(ref: str) -> tuple[str, int] | None:
    """'roster_2026R_1kurss:105' → ('roster_2026R_1kurss', 105)."""
    key, _, num = (ref or "").rpartition(":")
    return (key, int(num)) if key and num.isdigit() else None


def make_ref(roster_key: str, number: int) -> str:
    return f"{roster_key}:{number}"


# ── Matching lessons ──────────────────────────────────────────────────────────

def week_number(day: date, semester_start: date) -> int:
    """1 for the week the semester starts in, counting Mondays."""
    start_monday = semester_start - timedelta(days=semester_start.weekday())
    return (day - start_monday).days // 7 + 1


def _room_number(text: str | None) -> int | None:
    m = _FIRST_NUMBER.search(text or "")
    return int(m.group()) if m else None


def _entry_runs_on(entry: dict, week: int) -> bool:
    if entry.get("weeks") and week not in entry["weeks"]:
        return False
    parity = entry.get("parity")
    if parity == "1" and week % 2 == 0:
        return False
    if parity == "2" and week % 2 == 1:
        return False
    return True


def _matches(entry: dict, lesson, week: int) -> bool:
    if entry["module"] != lesson.module_id:
        return False
    if entry["time"] != lesson.time_start:
        return False
    if entry["day"] != _DAY_BY_WEEKDAY[lesson.date.weekday()]:
        return False
    if not _entry_runs_on(entry, week):
        return False
    # Parallel subgroups differ only by room, so check it when we know it.
    mine, theirs = _room_number(entry.get("room")), _room_number(lesson.room)
    if mine is not None and theirs is not None and mine != theirs:
        return False
    return True


def filter_lessons(student: dict, lessons: list, semester_start: date) -> list:
    """Keep only the lessons this student actually attends.

    A module absent from their entries entirely is left visible: a course added
    after the roster was published should look like an extra class, never like
    a missing one.
    """
    entries = student["entries"]
    known_modules = {e["module"] for e in entries}
    kept = []
    for lesson in lessons:
        if lesson.module_id not in known_modules:
            kept.append(lesson)
            continue
        week = week_number(lesson.date, semester_start)
        if any(_matches(e, lesson, week) for e in entries):
            kept.append(lesson)
    return kept


def missing_from_site(student: dict, lessons: list, semester_start: date,
                      for_date: date) -> list[dict]:
    """Sessions the roster promises on this date but the website never lists.

    The faculty's own timetable and its website do drift apart; when they do,
    the student should hear about it rather than quietly miss a class.
    """
    day  = _DAY_BY_WEEKDAY[for_date.weekday()]
    week = week_number(for_date, semester_start)
    on_site = {(l.module_id, l.time_start, _room_number(l.room)) for l in lessons
               if l.date == for_date}
    gaps = []
    for entry in student["entries"]:
        if entry["day"] != day or not _entry_runs_on(entry, week):
            continue
        room = _room_number(entry.get("room"))
        if any(m == entry["module"] and t == entry["time"] and (room is None or r == room)
               for m, t, r in on_site):
            continue
        gaps.append(entry)
    return gaps


# ── Subscriber-level helpers ──────────────────────────────────────────────────

def student_for(subscriber: dict) -> dict | None:
    """The roster entry a subscriber pinned themselves to, if any."""
    parsed = parse_ref(subscriber.get("roster_ref"))
    return get(*parsed) if parsed else None


def personalise(subscriber: dict, lessons: list, semester_start: date) -> list:
    """Narrow a whole year's timetable down to one subscriber's own classes."""
    student = student_for(subscriber)
    if not student:
        return lessons
    return filter_lessons(student, lessons, semester_start)


def keeps(subscriber: dict, lesson, semester_start: date) -> bool:
    """Would this subscriber see this one lesson? Used for alerts and reminders."""
    student = student_for(subscriber)
    if not student:
        return True
    return bool(filter_lessons(student, [lesson], semester_start))
