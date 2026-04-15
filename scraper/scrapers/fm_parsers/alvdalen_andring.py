"""Parser för Älvdalen ändring-formatet: veckonummer + veckodagskolumner.

Kännetecken:
    2026 Älvdalens skjutfält
    Vecka Måndag Tisdag Onsdag Torsdag Fredag Lördag Söndag Område
    15
    16
    18 12:30- 00:00- 00:00- 00:00- 00:00- 00:00- 00:00- 1-9
       24:00  24:00  24:00  24:00  24:00  24:00  24:00

Tider delas oftast på två rader: starttid med "-" på rad 1, sluttid på rad 2.
"""

import re
from datetime import date

from .base_parser import PDFParser, detect_type, format_time

# Detektering: "Vecka Måndag Tisdag" + Älvdalen
_HEADER_RE = re.compile(r"Vecka\s+Måndag\s+Tisdag", re.IGNORECASE)
_ALVDALEN_RE = re.compile(r"Älvdalen", re.IGNORECASE)

# Veckonummer i början av rad
_WEEK_LINE_RE = re.compile(r"^(\d{1,2})\b", re.MULTILINE)

# HH:MM- (start med trailing dash) eller HH:MM (end)
_PARTIAL_TIME_RE = re.compile(r"(\d{2}):(\d{2})-?")

# Sektor-mönster i slutet av rad
_SECTOR_RE = re.compile(r"(\d[\d,-]+\d)\s*$")


class AlvdalenAndringParser(PDFParser):
    """Parser för Älvdalen ändring: vecka-grid med veckodagskolumner."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(_ALVDALEN_RE.search(text)) and bool(_HEADER_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        year = _extract_year(text, filename)

        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            wm = re.match(r"^(\d{1,2})\s+(.+)", line)
            if not wm:
                i += 1
                continue

            week_num = int(wm.group(1))
            rest = wm.group(2)

            # Kolla om det finns tider (HH:MM)
            start_times = _PARTIAL_TIME_RE.findall(rest)
            if not start_times:
                i += 1
                continue

            # Extrahera sektor
            sm = _SECTOR_RE.search(rest)
            sectors = [sm.group(1)] if sm else ["all"]

            # Nästa rad har sluttider
            end_times: list[tuple[str, str]] = []
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if not re.match(r"^\d{1,2}\s", next_line) and _PARTIAL_TIME_RE.search(next_line):
                    end_times = _PARTIAL_TIME_RE.findall(next_line)
                    i += 1  # hoppa över slutraden

            # Para ihop start- och sluttider
            n_days = min(len(start_times), len(end_times)) if end_times else len(start_times)
            for day_idx in range(n_days):
                iso_day = day_idx + 1  # 1=Mon, 7=Sun
                try:
                    target_date = date.fromisocalendar(year, week_num, iso_day)
                except ValueError:
                    continue

                sh, sm_t = start_times[day_idx]
                if end_times and day_idx < len(end_times):
                    eh, em = end_times[day_idx]
                else:
                    continue  # Kan inte bilda komplett tidsintervall

                start = format_time(sh, sm_t)
                end = format_time(eh, em)
                restrictions.append({
                    "date": target_date.isoformat(),
                    "start": start,
                    "end": end,
                    "type": restriction_type,
                    "sectors": sectors,
                })

            i += 1

        restrictions.sort(key=lambda r: (r["date"], r["start"]))
        return restrictions


def _extract_year(text: str, filename: str) -> int:
    """Extrahera år."""
    m = re.search(r"20\d{2}", filename)
    if m:
        return int(m.group())
    m = re.search(r"20\d{2}", text)
    if m:
        return int(m.group())
    return date.today().year
