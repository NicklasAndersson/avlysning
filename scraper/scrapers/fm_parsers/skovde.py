"""Parser för Skövde-formatet: multi-week grid med VECKA N, dag+datum+klockslag.

Kännetecken:
    TILLTRÄDESFÖRBUD SKÖVDE SKJUTFÄLT
    VECKA 14           VECKA 15
    MÅNAD MARS/APRIL   MÅNAD APRIL
    DAG  DATUM  KLOCKSLAG   DAG  DATUM  KLOCKSLAG
    Måndag 31  07.00-16.00  Måndag 6  …
    Tisdag 1   …            Tisdag 7  …

Tider anges som "HH.MM-HH.MM" eller "HH.MM-HH:MM". "…" betyder ingen restriktion.
Datum som bara dag-nummer; veckonummer + MÅNAD-header bestämmer faktisk datum.
"""

import re
from datetime import date

from .base_parser import PDFParser, WEEKDAY_OFFSETS, detect_type, format_time

# VECKA N utan kolon (skiljer från standard_weekly "VECKA : N")
_VECKA_RE = re.compile(r"\bVECKA\s+(\d{1,2})\b", re.IGNORECASE)
_KLOCKSLAG_RE = re.compile(r"KLOCKSLAG", re.IGNORECASE)

# Veckodag + valfritt dagsnummer + tidsintervall
_WEEKDAY_RE = re.compile(
    r"(Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)"
    r"\s+\d{1,2}\s+"           # dagsnummer (ignoreras, beräknas från vecka)
    r"(\d{2})[.:](\d{2})\s*[-–]\s*(\d{2})[.:](\d{2})",
    re.IGNORECASE,
)

# ISO veckodag → isocalendar day (1=mån, 7=sön)
_WEEKDAY_ISO: dict[str, int] = {
    "måndag": 1, "tisdag": 2, "onsdag": 3, "torsdag": 4,
    "fredag": 5, "lördag": 6, "söndag": 7,
}


class SkovdeParser(PDFParser):
    """Parser för Skövde-format: VECKA N + KLOCKSLAG + dag+tid grid."""

    @staticmethod
    def can_parse(text: str) -> bool:
        has_vecka = bool(_VECKA_RE.search(text))
        no_colon = "VECKA :" not in text.upper()
        has_klockslag = bool(_KLOCKSLAG_RE.search(text))
        has_day_time = bool(_WEEKDAY_RE.search(text))
        return has_vecka and no_colon and has_klockslag and has_day_time

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        year = _extract_year(text, filename)

        # Samla alla vecko-positioner
        week_matches = list(_VECKA_RE.finditer(text))
        if not week_matches:
            return []

        for i, wm in enumerate(week_matches):
            week_num = int(wm.group(1))
            start_pos = wm.end()
            end_pos = week_matches[i + 1].start() if i + 1 < len(week_matches) else len(text)
            block = text[start_pos:end_pos]

            for dm in _WEEKDAY_RE.finditer(block):
                weekday_name = dm.group(1).lower()
                iso_day = _WEEKDAY_ISO.get(weekday_name)
                if not iso_day:
                    continue
                try:
                    target_date = date.fromisocalendar(year, week_num, iso_day)
                except ValueError:
                    continue
                start_t = format_time(dm.group(2), dm.group(3))
                end_t = format_time(dm.group(4), dm.group(5))
                restrictions.append({
                    "date": target_date.isoformat(),
                    "start": start_t,
                    "end": end_t,
                    "type": restriction_type,
                    "sectors": ["all"],
                })

        restrictions.sort(key=lambda r: (r["date"], r["start"]))
        return restrictions


def _extract_year(text: str, filename: str) -> int:
    """Extrahera år från filnamn eller text."""
    m = re.search(r"20\d{2}", filename)
    if m:
        return int(m.group())
    m = re.search(r"20\d{2}", text)
    if m:
        return int(m.group())
    return date.today().year
