"""Parser för Amf1-format (Stabbo, Väddö) med periodangivelser.

Kännetecken:
    Avser perioden: 2026-01-01 till 2026-12-31.
    Datum Veckodag Tid Område
    2026-01-15 Onsdag 08:00-17:00 A1

    eller:
    INGET TILLTRÄDESFÖRBUD RÅDER UNDER PERIODEN
"""

import re

from .base_parser import PDFParser, detect_type, format_time

# Detektering: "Avser perioden:"
PERIOD_RE = re.compile(r"Avser perioden:", re.IGNORECASE)

# "INGET TILLTRÄDESFÖRBUD"
NO_RESTRICTION_RE = re.compile(r"INGET TILLTR.{0,5}DESF.{0,5}RBUD", re.IGNORECASE)

# Datumrader: "2026-01-15 Onsdag 08:00-17:00"
AMF1_ROW_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s+"
    r"(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)\s+"
    r"(\d{2})[.:](\d{2})\s*[-–]\s*(\d{2})[.:](\d{2})",
    re.IGNORECASE,
)


class Amf1Parser(PDFParser):
    """Parser för Amf1-format (Stabbo, Väddö) med tidstabell eller 'inget förbud'."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(PERIOD_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        if NO_RESTRICTION_RE.search(text):
            return []

        restriction_type = detect_type(text)
        restrictions: list[dict] = []

        for match in AMF1_ROW_RE.finditer(text):
            restrictions.append({
                "date": match.group(1),
                "start": format_time(match.group(2), match.group(3)),
                "end": format_time(match.group(4), match.group(5)),
                "type": restriction_type,
                "sectors": ["all"],
            })

        return restrictions
