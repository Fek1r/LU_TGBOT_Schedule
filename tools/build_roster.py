"""Turn the faculty's two PDFs into one JSON roster the bot can load.

Run by hand whenever the faculty publishes a new distribution list:

    pip install pypdf
    python tools/build_roster.py \
        --students ~/Downloads/1kurss_2026R_sad_gr_07-PUBL.pdf \
        --days     ~/Downloads/2026R_DN_LV_09.pdf \
        --out      data/roster_2026R_1kurss.json

The bot never parses PDFs at runtime — it just reads the JSON.
"""
import argparse
import collections
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _pdf_parse import parse_dn, parse_students


# Names never reach the repository. Each name token is hashed instead, so the
# bot can still answer "is this you?" without publishing a class roster.
# For a known 227-person cohort this is obfuscation, not anonymity: anyone with
# a list of Latvian surnames could grind through it. It stops casual copying.
SALT = "lu-schedule-bot/roster/v1"


def _fold(text: str) -> str:
    stripped = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in stripped if not unicodedata.combining(c))


def name_hashes(name: str) -> list[str]:
    return [
        hashlib.sha256((SALT + token).encode()).hexdigest()[:16]
        for token in _fold(name).split()
    ]


def build(students_pdf: str, days_pdf: str, name: str) -> dict:
    sessions = parse_dn(days_pdf)
    students = parse_students(students_pdf)

    by_label, by_slot = {}, collections.defaultdict(list)
    for e in sessions:
        by_slot[(e["day"], e["time"])].append(e)
        for label in e["labels"]:
            by_label[(e["day"], e["time"], label)] = e

    def resolve(tok):
        if tok["label"]:
            return by_label.get((tok["day"], tok["time"], tok["label"]))
        plain = [e for e in by_slot.get((tok["day"], tok["time"]), []) if not e["labels"]]
        return plain[0] if plain else None

    out_students, unresolved = [], 0
    for s in students:
        entries = []
        for tok in s["tokens"]:
            found = resolve(tok)
            if not found:
                unresolved += 1
                continue
            entries.append({
                "day":    tok["day"],
                "time":   tok["time"],
                "parity": tok["par"],          # "1" odd weeks, "2" even weeks, None every
                "label":  tok["label"],        # subgroup, or None for a whole-year lecture
                "module": found["module"],
                "kind":   found["kind"],       # lek / lab / pr / sem
                "room":   found["room"],
                "weeks":  found["weeks"],
            })
        out_students.append({"n": s["n"], "h": name_hashes(s["name"]),
                             "flow": s["flow"], "entries": entries})

    if unresolved:
        print(f"WARNING: {unresolved} cells could not be resolved", file=sys.stderr)

    return {"name": name, "students": out_students}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--students", required=True)
    ap.add_argument("--days", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="2026R 1. kurss")
    args = ap.parse_args()

    data = build(args.students, args.days, args.name)
    Path(args.out).write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    total = sum(len(s["entries"]) for s in data["students"])
    print(f"{args.out}: {len(data['students'])} students, {total} sessions")


if __name__ == "__main__":
    main()
