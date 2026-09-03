"""The university's group index — all 1669 of them, scraped once and cached.

The site publishes every group as a plain <a href="/grupa/<id>/nedela"> on its
front page, so a single request gets us a searchable catalogue. No API needed,
which is fortunate, because there isn't one.
"""
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://lekciju-saraksts.lu.lv"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; LU-Schedule-Bot/1.0)"}

_TTL       = 24 * 3600          # the catalogue changes about once a semester
_LINK_RE   = re.compile(r"^/grupa/([^/]+)/nedela$")

_cache: list[tuple[str, str]] = []
_fetched_at: float = 0.0


def _load() -> list[tuple[str, str]]:
    resp = requests.get(f"{BASE_URL}/", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for a in soup.find_all("a"):
        m = _LINK_RE.match(a.get("href") or "")
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        out.append((m.group(1), " ".join(a.get_text(" ", strip=True).split())))
    return out


def refresh(force: bool = False) -> list[tuple[str, str]]:
    """Return the catalogue, refetching it when stale.

    On failure the previous catalogue is kept — a stale group list beats no
    group list, and it only goes out of date once a semester anyway.
    """
    global _cache, _fetched_at
    if _cache and not force and time.time() - _fetched_at < _TTL:
        return _cache
    try:
        fresh = _load()
        if fresh:
            _cache, _fetched_at = fresh, time.time()
            logger.info("Group index loaded: %d groups", len(fresh))
        else:
            logger.warning("Group index came back empty — keeping %d cached", len(_cache))
    except Exception as exc:
        logger.error("Could not refresh group index: %s", exc)
    return _cache


def search(query: str, limit: int = 10) -> list[tuple[str, str]]:
    """Every whitespace-separated term must appear in the id or the name."""
    terms = query.lower().split()
    if not terms:
        return []
    hits = [
        (gid, name)
        for gid, name in refresh()
        if all(t in gid.lower() or t in name.lower() for t in terms)
    ]
    return hits[:limit]


def exists(group_id: str) -> bool:
    return any(gid == group_id for gid, _ in refresh())


def name_of(group_id: str) -> str:
    for gid, name in refresh():
        if gid == group_id:
            return name
    return group_id


def short_name(group_id: str) -> str:
    """Squeeze '26R-22302 Datorzinātnes Akadēmiskā bakalaura,Pilna laika:
    klātiene,1-sem.' down to something that fits on a button."""
    name = name_of(group_id)
    if name == group_id:
        return group_id
    parts = [p.strip() for p in name.split(",") if p.strip()]
    head = parts[0]
    code, _, programme = head.partition(" ")
    programme = programme or head
    # Drop the degree boilerplate — every group in the list has some.
    for noise in ("Akadēmiskā bakalaura", "Akadēmiskā maģistra", "Profesionālā bakalaura",
                  "Profesionālā maģistra", "Īsā cikla profesionālās augstākās izglītības"):
        programme = programme.replace(noise, "")
    programme = " ".join(programme.split())
    # Everything from the semester onwards: '3-sem.' plus any specialisation
    # suffix like 'DI a.prog.', which is the only thing telling -DI from -DZ apart.
    sem_at = next((i for i, p in enumerate(parts) if p.endswith("sem.")), None)
    rest = parts[sem_at:] if sem_at is not None else []
    tail = ", ".join(x for x in [programme, *rest] if x)
    return f"{group_id} · {tail}" if tail else group_id
