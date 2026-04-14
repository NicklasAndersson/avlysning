"""Parser för Tåme-format med VECKA YYWW och YY-MM-DD-datum.

Kännetecken:
    VECKA 2617
    26-04-20 -- 26-04-26
    DAG DAT OMR Riskområdets begränsningar
    Lördag 25 A,B,1_8 N 68 S 191 6200
    0700-1730
"""

import re
from datetime import date, timedelta

from .base_parser import (
    PDFParser,
    TIME_RANGE_RE,
    WEEKDAY_OFFSETS,
    detect_type,
    format_time,
)

# Detektering: "VECKA YYWW" (4 siffror utan kolon)
TAME_WEEK_RE = re.compile(r"VECKA\s+\d{4}\b", re.IGNORECASE)

# Datumintervall: "26-04-20 -- 26-04-26"
TAME_DATE_RANGE_RE = re.compile(
    r"(\d{2}-\d{2}-\d{2})\s*[-–]+\s*(\d{2}-\d{2}-\d{2})"
)


def _parse_short_date(s: str) -> date:
    """Parsar YY-MM-DD till date."""
    parts = s.split("-")
    return date(2000 + int(parts[0]), int(parts[1]), int(parts[2]))


class TameParser(PDFParser):
    """Parser för Tåme-format med VECKA YYWW."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(TAME_WEEK_RE.search(text)) and bool(TAME_DATE_RANGE_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        range_match = TAME_DATE_RANGE_RE.search(text)
        if not range_match:
            return []

        start_date = _parse_short_date(range_match.group(1))
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        lines = text.split("\n")

        current_day_offset: int | None = None
        for line in lines:
            line_lower = line.lower().strip()

            for day_name, offset in WEEKDAY_OFFSETS.items():
                if line_lower.startswith(day_name):
                    current_day_offset = offset
                    break

            if current_day_offset is None:
                continue

            time_matches = TIME_RANGE_RE.findall(line)
            if time_matches:
                target_date = start_date + timedelta(days=current_day_offset)
                for h1, m1, h2, m2 in time_matches:
                    restrictions.append({
                        "date": target_date.isoformat(),
                        "start": format_time(h1, m1),
                        "end": format_time(h2, m2),
                        "type": restriction_type,
                        "sectors": ["all"],
                    })

        return restrictions
