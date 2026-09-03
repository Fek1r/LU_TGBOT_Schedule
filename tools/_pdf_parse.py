"""Разбор двух PDF ЛУ: кто в какой подгруппе и когда эта подгруппа сидит."""
import re
from pypdf import PdfReader

DAYS = {"PIRMDIENA":"Pr","OTRDIENA":"O","TRESDIENA":"T","TREŠDIENA":"T",
        "CETURTDIENA":"C","PIEKTDIENA":"Pk"}
MID   = re.compile(r'^\s*(?P<flow>[A-Za-z]{1,6})\s+(?P<mod>[A-Za-zĀ-ž]{3,6}B\d{3})\s+(?P<rest>.+)$')
TIME  = re.compile(r'^\s*(\d{1,2})\.(\d{2})\s*[–-]')
CONT  = {"09:25","11:25","13:25","15:25","17:20","19:05","20:50"}
TYPE  = re.compile(r'\b(lab\.\s*d\.|pr\.\s*d\.|sem\.)')
LABEL = re.compile(r'\(([^)]*)\)')
ROOM  = re.compile(r'(\d{1,3})\.\s*(?:t\.|auditorija|datorklase)?\s*$')

def parse_dn(path, pages=range(5)):
    """→ [{day,time,module,kind,labels,room,staff}]"""
    out=[]
    r=PdfReader(path)
    for i in pages:
        txt=r.pages[i].extract_text() or ""
        letters="".join(l.strip() for l in txt.splitlines() if len(l.strip())==1).upper()
        day=next((v for k,v in DAYS.items() if k in letters), "?")
        cur=None
        for ln in txt.splitlines():
            m=TIME.match(ln)
            if m:
                t=f"{int(m.group(1)):02d}:{m.group(2)}"
                if t not in CONT: cur=t
                continue
            e=MID.match(ln)
            if not e:
                # продолжение предыдущей записи: аудитория и недели часто на 2-й строке
                if out and cur and ln.strip() and out[-1].get("_open"):
                    out[-1]["raw"] += " " + " ".join(ln.split())
                continue
            if not cur: continue
            rest=e.group("rest")
            tm=TYPE.search(rest)
            kind={"lab":"lab","pr":"pr","sem":"sem"}.get(
                (tm.group(1)[:3].replace(".","").strip() if tm else "lek"), "lek")
            kind = "lab" if tm and tm.group(1).startswith("lab") else \
                   "pr"  if tm and tm.group(1).startswith("pr")  else \
                   "sem" if tm and tm.group(1).startswith("sem") else "lek"
            # подгруппы — только то, что стоит ПОСЛЕ вида занятия
            out.append(dict(day=day, time=cur, module=e.group("mod"), kind=kind,
                            raw=" ".join(rest.split()), _open=True))
    for e in out:
        e.pop("_open", None)
        raw = e["raw"]
        tm  = TYPE.search(raw)
        tail = raw[tm.end():] if tm else ""
        labels, weeks = set(), None
        for grp in LABEL.findall(tail):
            if "ned" in grp:                     # (5., 8., 10., 14., 16. ned.)
                weeks = [int(x) for x in re.findall(r'\d+', grp)]
                continue
            for part in re.split(r'[/,]', grp):
                part = part.strip().rstrip(".")
                if part and part != "--" and len(part) <= 3:
                    labels.add(part)
        rm = ROOM.search(raw.strip())
        e.update(labels=labels, weeks=weeks, room=rm.group(1) if rm else None)
    return out

TOKEN = re.compile(r'(?:(?P<par>[12])\.)?(?P<day>Pr|Pk|O|T|C)-(?P<h>\d{1,2})\.(?P<m>\d{2})'
                   r'(?:\s*\((?P<label>[^)]{1,3})\))?')

def parse_students(path):
    """→ [{n,name,flow,tokens:[{par,day,time,label}]}]"""
    r=PdfReader(path); out=[]
    for p in r.pages:
        for ln in p.extract_text(extraction_mode="layout").splitlines():
            m=re.match(r'^\s*(\d{1,3})\s{2,}(.+?)\s{2,}([IV]{1,2})\s{2,}(.*)$', ln)
            if not m: continue
            num, who, flow, rest = m.groups()
            name=" ".join(who.split())
            toks=[{"par":t.group("par"), "day":t.group("day"),
                   "time":f"{int(t.group('h')):02d}:{t.group('m')}",
                   "label":(t.group("label") or "").strip() or None}
                  for t in TOKEN.finditer(rest)]
            out.append(dict(n=int(num), name=name, flow=flow, tokens=toks))
    return out
