"""Language-aware message formatting."""
from datetime import date, datetime as _dt
from html import escape

from scraper import Lesson
from locales import LOCALES, t


def _day_name(d: date, lv_key: str, lang: str) -> str:
    key  = lv_key or ["Pr", "Ot", "Tr", "Ce", "Pk", "Se", "Sv"][d.weekday()]
    days = LOCALES.get(lang, LOCALES["ru"])["days"]
    return days.get(key, key)


def _ev_type(event_type: str, lang: str) -> str:
    """Return the correct half of 'Lekcija | Lecture' for the given language."""
    if "|" not in event_type:
        return event_type
    lv_part, en_part = [p.strip() for p in event_type.split("|", 1)]
    if lang == "lv":
        return lv_part
    return en_part  # ru and en both use the English label


def lesson_title(lesson: Lesson, lang: str) -> str:
    if lang == "en" and lesson.title_en:
        return lesson.title_en
    return lesson.title


def fmt_lesson(lesson: Lesson, lang: str) -> str:
    title = escape(lesson_title(lesson, lang))
    ev    = _ev_type(lesson.event_type, lang)

    header = f"┌ {lesson.time_start} – {lesson.time_end}"
    if ev:
        header += f" ─ {escape(ev)}"

    if lesson.is_cancelled:
        label = t(lang, "cancelled_label")
        return f"{header} ❌\n│ 📚 <s>{title}</s>\n└ <b>{label}</b>"

    middle: list[str] = [f"│ 📚 <b>{title}</b>"]

    if lesson.online:
        middle.append(f"│ 🌐 <i>{t(lang, 'online_label')}</i>")
    elif lesson.room:
        loc = escape(lesson.room)
        if lesson.room_building and lesson.room_building not in ("", "None"):
            loc += f", {escape(lesson.room_building)}"
        middle.append(f"│ 🏛 {loc}")

    if lesson.staff:
        bottom = f"└ 👤 {escape(lesson.staff)}"
    else:
        last   = middle.pop()
        bottom = "└" + last[1:]

    return "\n".join([header] + middle + [bottom])


def _break_minutes(end: str, start: str) -> int:
    e = _dt.strptime(end, "%H:%M")
    s = _dt.strptime(start, "%H:%M")
    return max(0, int((s - e).total_seconds() // 60))


def fmt_day(lessons: list[Lesson], for_date: date, lang: str) -> str:
    seen: set[tuple] = set()
    unique: list[Lesson] = []
    for l in lessons:
        if l.date != for_date:
            continue
        key = (l.time_start, l.time_end, l.module_id, l.staff, l.room)
        if key not in seen:
            seen.add(key)
            unique.append(l)
    day_lessons = sorted(unique, key=lambda l: l.time_start)
    lv_key = day_lessons[0].day if day_lessons else ""
    header = f"📅 <b>{_day_name(for_date, lv_key, lang)}, {for_date.strftime('%d.%m.%Y')}</b>"

    if not day_lessons:
        return f"{header}\n\n{t(lang, 'no_classes')}"

    blocks: list[str] = []
    for i, lesson in enumerate(day_lessons):
        blocks.append(fmt_lesson(lesson, lang))
        if i < len(day_lessons) - 1:
            gap = _break_minutes(lesson.time_end, day_lessons[i + 1].time_start)
            if gap > 0:
                blocks.append(t(lang, "break", minutes=gap))

    return header + "\n\n" + "\n\n".join(blocks)


def fmt_week(lessons: list[Lesson], lang: str) -> list[str]:
    """Return one formatted string per day that has lessons."""
    unique_dates = sorted({l.date for l in lessons})
    return [fmt_day(lessons, d, lang) for d in unique_dates]
