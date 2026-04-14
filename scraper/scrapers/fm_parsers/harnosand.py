"""Parser för Härnösand-format med DD/M-datum i header och ISO-datum per rad.

Kännetecken:
    VECKA : 17 DATUM : 20/4 - 26/4 - 2026
    Måndag         Ingen     Inte
    2026-04-20     Farlig    Tillträdesförbud
    Torsdag        Västernorrlands-    Avspärrat ÖSG
    2026-04-23     gruppen             Omr 2 - 6
    07.00-24.00    Skarpskjutning

Varje dag har: veckodag på en rad, ISO-datum på nästa, tid på ytterligare en rad.
"""

import re
from datetime import date

from .base_parser import PDFParser, TIME_RANGE_RE, detect_type, format_time

# Detektering: "DATUM : DD/M" format (skiljer från standard_weekly som har ISO-datum)
HARNOSAND_HEADER_RE = re.compile(r"DATUM\s*:\s*\d{1,2}/\d{1,2}\s*-", re.IGNORECASE)

# ISO-datum i text
ISO_DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")


class HarnosandParser(PDFParser):
    """Parser för Härnösand-format med ISO-datum per rad."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(HARNOSAND_HEADER_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        lines = text.split("\n")

        current_date: str | None = None

        for line in lines:
            stripped = line.strip()

            # Hitta ISO-datum
            date_match = ISO_DATE_RE.search(stripped)
            if date_match:
                current_date = date_match.group(1)

            # Hitta tidsintervall
            time_matches = TIME_RANGE_RE.findall(stripped)
            if time_matches and current_date:
                for h1, m1, h2, m2 in time_matches:
                    restrictions.append({
                        "date": current_date,
                        "start": format_time(h1, m1),
                        "end": format_time(h2, m2),
                        "type": restriction_type,
                        "sectors": ["all"],
                    })

        return restrictions
