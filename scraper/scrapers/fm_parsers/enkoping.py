"""Parser för Enköpings-formatet: FEKN-grid med X-markeringar per delområde.

Kännetecken:
    Enköpings närövningsfält
    VECKA 616
    Måndag Tisdag Onsdag Torsdag Fredag Lördag Söndag
    Del-
    13 april 14 april 15 april 16 april 17 april 18 april 19 april
    område
    F E K N F E K N F E K N ...
    X X X X X X X X ...
    A/B/C/...

Dygnsindelning:
    F = Förmiddag 07-12
    E = Eftermiddag 12-17
    K = Kväll 17-22
    N = Natt 22-07

Varje X i en FEKN-kolumn för en veckodag innebär restriktion under den tidsperioden.
Delområde anges som A-L.
"""

import re
from datetime import date

from .base_parser import PDFParser, SWEDISH_MONTHS, detect_type

# Detektering
_ENKOPING_RE = re.compile(r"Enköpings\s+närövningsfält", re.IGNORECASE)
_FEKN_RE = re.compile(r"F\s+E\s+K\s+N\s+F\s+E\s+K\s+N")

# VECKA 6NN
_VECKA_6_RE = re.compile(r"\bVECKA\s+6(\d{2})\b", re.IGNORECASE)

# Datumrad: "DD månad DD månad ..."
_DATE_ROW_RE = re.compile(
    r"(\d{1,2})\s+(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)"
    r"(?:\s+(\d{1,2})\s+(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december))*",
    re.IGNORECASE,
)

# Enskilt datum i raden
_SINGLE_DATE_RE = re.compile(
    r"(\d{1,2})\s+(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)",
    re.IGNORECASE,
)

# FEKN tidsperioder
FEKN_TIMES = {
    "F": ("07:00", "12:00"),
    "E": ("12:00", "17:00"),
    "K": ("17:00", "22:00"),
    "N": ("22:00", "07:00"),
}


class EnkopingParser(PDFParser):
    """Parser för Enköping: FEKN-grid → dagliga restriktioner per delområde."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(_ENKOPING_RE.search(text)) and bool(_FEKN_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        year = _extract_year(text, filename)

        # Hitta datumrader (7 datum = mån-sön)
        dates: list[date] = []
        for m in _SINGLE_DATE_RE.finditer(text):
            day = int(m.group(1))
            month = SWEDISH_MONTHS.get(m.group(2).lower())
            if month:
                try:
                    dates.append(date(year, month, day))
                except ValueError:
                    pass
            if len(dates) >= 7:
                break

        if not dates:
            return []

        # Hitta alla X-markeringar efter FEKN-headern
        # Varje dag har 4 kolumner (F, E, K, N), 7 dagar = 28 kolumner
        # Parse rader med X-markeringar och koppla till delområden
        lines = text.split("\n")
        fekn_header_found = False
        seen: set[tuple[str, str, str]] = set()

        for line in lines:
            if "F E K N" in line.replace("  ", " "):
                fekn_header_found = True
                continue

            if not fekn_header_found:
                continue

            # Stoppa vid "Dygnsindelning" eller "Områden för"
            if re.search(r"Dygnsindelning|Områden för|Bokning", line, re.IGNORECASE):
                break

            # Kolla om raden har X-markeringar
            if "X" not in line:
                continue

            # Hitta positioner för alla X i raden
            x_positions = [i for i, c in enumerate(line) if c == "X"]
            if not x_positions:
                continue

            # Varje FEKN-grupp upptar ungefär samma bredder
            # Mappa X-position → (dag_index, period_index)
            for xpos in x_positions:
                # Uppskatta vilken dag och period
                # FEKN-headern har jämnt fördelade kolumner
                group_width = len(line) / max(len(dates), 7)
                day_idx = min(int(xpos / group_width), len(dates) - 1)
                # Inom gruppen: vilken av FEKN?
                within = (xpos % max(int(group_width), 1))
                period_width = max(int(group_width / 4), 1)
                period_idx = min(within // period_width, 3)

                periods = ["F", "E", "K", "N"]
                period = periods[period_idx]
                start, end = FEKN_TIMES[period]

                if day_idx < len(dates):
                    d = dates[day_idx]
                    key = (d.isoformat(), start, end)
                    if key not in seen:
                        seen.add(key)
                        restrictions.append({
                            "date": d.isoformat(),
                            "start": start,
                            "end": end,
                            "type": restriction_type,
                            "sectors": ["all"],
                        })

        # Sammanfoga angränsande tidsperioder per dag
        restrictions = _merge_adjacent(restrictions)
        restrictions.sort(key=lambda r: (r["date"], r["start"]))
        return restrictions


def _merge_adjacent(restrictions: list[dict]) -> list[dict]:
    """Sammanfoga angränsande tidsperioder för samma dag."""
    by_date: dict[str, list[dict]] = {}
    for r in restrictions:
        by_date.setdefault(r["date"], []).append(r)

    merged: list[dict] = []
    for d, entries in by_date.items():
        entries.sort(key=lambda r: r["start"])
        current = entries[0].copy()
        for entry in entries[1:]:
            if entry["start"] <= current["end"]:
                current["end"] = max(current["end"], entry["end"])
            else:
                merged.append(current)
                current = entry.copy()
        merged.append(current)
    return merged


def _extract_year(text: str, filename: str) -> int:
    """Extrahera år."""
    m = re.search(r"20\d{2}", filename)
    if m:
        return int(m.group())
    m = re.search(r"20\d{2}", text)
    if m:
        return int(m.group())
    return date.today().year
