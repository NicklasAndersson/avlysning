"""Parser för Härad-formatet: VECKA 6NN + veckodag DD mon + tidsintervall.

Kännetecken:
    Härads skjutfält R 37
    Tillträdesförbud!
    VECKA 615
    Måndag 06 apr -
    Tisdag 07 apr 0900-1930 1000-1600 1)
    Onsdag 08 apr 0900-1930

"-" betyder ingen restriktion den dagen.
Kan ha flera tidsintervall per rad (olika kolumner i PDF).
"VECKA 6NN" = år 2026, vecka NN (t.ex. 615 → vecka 15).
"""

import re
from datetime import date

from .base_parser import PDFParser, SWEDISH_MONTHS, detect_type, format_time

# Detektering: "VECKA 6\d{2}" + "Tillträdesförbud" + veckodag DD mon
_VECKA_6_RE = re.compile(r"\bVECKA\s+6(\d{2})\b", re.IGNORECASE)
_HARAD_RE = re.compile(r"Härads\s+skjutfält", re.IGNORECASE)

# Rad: veckodag + DD + månad-förk. + tidsintervall(er)
_DAY_RE = re.compile(
    r"(Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)"
    r"\s+(\d{1,2})\s+(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)",
    re.IGNORECASE,
)

# Tidsintervall (HHMM-HHMM eller HH:MM-HH:MM)
_TIME_RE = re.compile(r"(\d{2})(\d{2})\s*-\s*(\d{2})(\d{2})")


class HaradParser(PDFParser):
    """Parser för Härad-format: VECKA 6NN + veckodag DD mon + tid."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(_HARAD_RE.search(text)) and bool(_VECKA_6_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        year = _extract_year(text, filename)

        lines = text.split("\n")
        for i, line in enumerate(lines):
            dm = _DAY_RE.search(line)
            if not dm:
                continue

            day = int(dm.group(2))
            month_name = dm.group(3).lower()
            month = SWEDISH_MONTHS.get(month_name)
            if not month:
                continue
            try:
                target_date = date(year, month, day)
            except ValueError:
                continue

            # Hitta alla tidsintervall efter datum-matchningen
            rest = line[dm.end():]
            # Samla även nästa rad om den börjar med tid (multi-row)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if _TIME_RE.match(next_line):
                    rest += " " + next_line

            times = _TIME_RE.findall(rest)
            for h1, m1, h2, m2 in times:
                start = format_time(h1, m1)
                end = format_time(h2, m2)
                restrictions.append({
                    "date": target_date.isoformat(),
                    "start": start,
                    "end": end,
                    "type": restriction_type,
                    "sectors": ["all"],
                })

        restrictions.sort(key=lambda r: (r["date"], r["start"]))
        return restrictions


def _extract_year(text: str, filename: str) -> int:
    """Extrahera år. Försöker VECKA 6NN → 2026, annars filnamn/text."""
    m = _VECKA_6_RE.search(text)
    if m:
        return 2026  # "6" = 2026 i FM:s format

    m = re.search(r"20\d{2}", filename)
    if m:
        return int(m.group())
    m = re.search(r"20\d{2}", text)
    if m:
        return int(m.group())
    return date.today().year
