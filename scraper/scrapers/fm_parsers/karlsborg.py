"""Parser för Karlsborg-formatet: veckoschema med VECKA:6NN och tidspar.

Kännetecken:
    VECKA: 616
    Kråks skjutfält Nytorps skjutfält Vispås hgr.bana
    Dag Dat
    från till från till från till
    0800 2030
    Mån 13
    ...

Tider kan stå antingen före eller efter daglinjen.
Kolumnerna (Kråk/Nytorp/Vispås) går förlorade vid textextraktion,
så vi behandlar alla tider som "all" sektorer.
"""

import re
from datetime import date

from .base_parser import PDFParser, detect_type

# Detektering
_VECKA_6_RE = re.compile(r"VECKA:\s*6(\d{2})\b", re.IGNORECASE)
_KARLSBORG_RE = re.compile(
    r"Kråk|Nytorp|Vispås|Karlsborg",
    re.IGNORECASE,
)

# Daglinjer: "Mån 13", "Tis 14" etc.
_DAY_RE = re.compile(
    r"^(Mån|Tis|Ons|Tors|Fre|Lör|Sön)\s+(\d{1,2})$",
    re.IGNORECASE,
)

# Tidspar: "0800 2030" (4-siffrig tid × 2)
_TIME_RE = re.compile(r"^(\d{4})\s+(\d{4})$")


class KarlsborgParser(PDFParser):
    """Parser för Karlsborg: veckoschema med VECKA:6NN."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(_VECKA_6_RE.search(text)) and bool(_KARLSBORG_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []

        m = _VECKA_6_RE.search(text)
        if not m:
            return []
        week_num = int(m.group(1))
        year = 2026  # 6NN → 2026

        lines = text.split("\n")

        # Hitta alla dagar och tider
        # Strategi: gå igenom raderna, matcha dag-rader och tid-rader.
        # Koppla tider till närmaste dag (tid före dag = den dagen, tid efter dag = den dagen).
        day_entries: list[tuple[int, int]] = []  # (line_index, day_of_month)
        time_entries: list[tuple[int, str, str]] = []  # (line_index, start, end)

        for i, line in enumerate(lines):
            line = line.strip()
            dm = _DAY_RE.match(line)
            if dm:
                day_entries.append((i, int(dm.group(2))))
                continue
            tm = _TIME_RE.match(line)
            if tm:
                raw_start = tm.group(1)
                raw_end = tm.group(2)
                start = f"{raw_start[:2]}:{raw_start[2:]}"
                end = f"{raw_end[:2]}:{raw_end[2:]}"
                time_entries.append((i, start, end))

        # Koppla tider till dagar: hitta den dag som är närmast varje tid (inom 2 rader)
        for t_idx, start, end in time_entries:
            best_day: int | None = None
            best_dist = 999
            for d_idx, day_num in day_entries:
                dist = abs(t_idx - d_idx)
                if dist < best_dist:
                    best_dist = dist
                    best_day = day_num
            if best_day is not None and best_dist <= 2:
                # Beräkna datum från veckonummer
                month = _month_for_day(year, week_num, best_day)
                if month:
                    try:
                        d = date(year, month, best_day)
                        restrictions.append({
                            "date": d.isoformat(),
                            "start": start,
                            "end": end,
                            "type": restriction_type,
                            "sectors": ["all"],
                        })
                    except ValueError:
                        pass

        restrictions.sort(key=lambda r: (r["date"], r["start"]))
        return restrictions


def _month_for_day(year: int, week_num: int, day_of_month: int) -> int | None:
    """Givet veckonummer, ta reda på vilken månad dag-numret hör till.

    Veckan kan spänna över månadsskifte, så vi testar alla 7 dagar
    i veckan och hittar den som matchar day_of_month.
    """
    for iso_day in range(1, 8):
        try:
            d = date.fromisocalendar(year, week_num, iso_day)
            if d.day == day_of_month:
                return d.month
        except ValueError:
            continue
    return None
