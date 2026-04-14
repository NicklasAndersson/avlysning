"""Parser för Marma-format med YYMMDD-datum.

Kännetecken:
    V.612
    Måndag 260316 00.00 - 24.00
    Tisdag 260317 00.00 - 24.00
    Lördag Inget tillträdesförbud
"""

import re
from datetime import date

from .base_parser import PDFParser, detect_type, format_time

# Detektering: "V." + 3-4-siffrig veckokod OCH 6-siffriga datum efter veckodag
MARMA_WEEK_RE = re.compile(r"V\.\s*\d{3,4}")

# Datumrader: "Måndag 260316 00.00 - 24.00"
MARMA_ROW_RE = re.compile(
    r"(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)\s+"
    r"(\d{6})\s+"
    r"(\d{2})[.:](\d{2})\s*[-–]\s*(\d{2})[.:](\d{2})",
    re.IGNORECASE,
)


class MarmaParser(PDFParser):
    """Parser för Marma-format med YYMMDD-datum och HH.MM-tider."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(MARMA_WEEK_RE.search(text)) and bool(MARMA_ROW_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []

        for match in MARMA_ROW_RE.finditer(text):
            date_str = match.group(1)  # YYMMDD
            year = 2000 + int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])

            try:
                d = date(year, month, day)
            except ValueError:
                continue

            restrictions.append({
                "date": d.isoformat(),
                "start": format_time(match.group(2), match.group(3)),
                "end": format_time(match.group(4), match.group(5)),
                "type": restriction_type,
                "sectors": ["all"],
            })

        return restrictions
