"""Parser för Kalixfors-formatet: DATUM med datumspann.

Kännetecken:
    KALIXFORS SKJUTFÄLT
    TILLTRÄDESFÖRBUD!
    VECKA : 18-22 DATUM : 2026-04-27--0531
    Ingen skjutning under perioden ...

Datumspannet tolkas som YYYY-MM-DD--MMDD (slut-månad+dag).
Hela perioden ger dagliga restriktioner 00:00-24:00.
"""

import re
from datetime import date, timedelta

from .base_parser import PDFParser, detect_type

# Detektering
_KALIXFORS_RE = re.compile(r"KALIXFORS\s+SKJUTF", re.IGNORECASE)
_DATUM_RE = re.compile(
    r"DATUM\s*:\s*(\d{4})-(\d{2})-(\d{2})--(\d{2})(\d{2})",
    re.IGNORECASE,
)


class KalixforsParser(PDFParser):
    """Parser för Kalixfors: datumspann YYYY-MM-DD--MMDD."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(_KALIXFORS_RE.search(text)) and bool(_DATUM_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []

        m = _DATUM_RE.search(text)
        if not m:
            return []

        year = int(m.group(1))
        start_month = int(m.group(2))
        start_day = int(m.group(3))
        end_month = int(m.group(4))
        end_day = int(m.group(5))

        try:
            start_date = date(year, start_month, start_day)
            end_date = date(year, end_month, end_day)
        except ValueError:
            return []

        current = start_date
        while current <= end_date:
            restrictions.append({
                "date": current.isoformat(),
                "start": "00:00",
                "end": "24:00",
                "type": restriction_type,
                "sectors": ["all"],
            })
            current += timedelta(days=1)

        return restrictions
