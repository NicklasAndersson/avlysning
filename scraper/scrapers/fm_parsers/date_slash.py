"""Parser för DD/M datumformat (Nyårsåsen, Vällinge).

Kännetecken:
    13/4 Måndag 0800-2200 Skarpskjutning       (Nyårsåsen)
    16 Torsdag 16/4 09:00-15:00                 (Vällinge)

Året hämtas från kontextdatum i PDF-texten (t.ex. "2026-04-13--2026-04-21")
eller från filnamnet.
"""

import re
from datetime import date

from .base_parser import PDFParser, detect_type, format_time

# DD/M eller D/M datum
DATE_SLASH_RE = re.compile(
    r"(\d{1,2})/(\d{1,2})\s+"
    r"(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)?\s*"
    r"(\d{2})[.:]?(\d{2})\s*[-–]\s*(\d{2})[.:]?(\d{2})",
    re.IGNORECASE,
)

# Detektering: DD/M följt av tidsintervall
DETECT_RE = re.compile(r"\b\d{1,2}/\d{1,2}\s+.*?\d{2}[.:]?\d{2}\s*[-–]")


def _extract_year(filename: str, text: str) -> int:
    """Extraherar år från filnamnet, texten, eller använder innevarande år."""
    m = re.search(r"20\d{2}", filename)
    if m:
        return int(m.group())
    m = re.search(r"20\d{2}", text)
    if m:
        return int(m.group())
    return date.today().year


class DateSlashParser(PDFParser):
    """Parser för PDF:er med DD/M datumformat."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(DETECT_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        year = _extract_year(filename, text)
        restriction_type = detect_type(text)
        restrictions: list[dict] = []

        for match in DATE_SLASH_RE.finditer(text):
            day = int(match.group(1))
            month = int(match.group(2))
            h1, m1 = match.group(3), match.group(4)
            h2, m2 = match.group(5), match.group(6)

            try:
                d = date(year, month, day)
            except ValueError:
                continue

            restrictions.append({
                "date": d.isoformat(),
                "start": format_time(h1, m1),
                "end": format_time(h2, m2),
                "type": restriction_type,
                "sectors": ["all"],
            })

        return restrictions
