"""Parser för standardformat med veckoschema (Arvidsjaur, Dagsådalen, Tjärnmyran, Boden).

Kännetecken:
    VECKA : 16 DATUM : 20260413-20260419
    DAG OCH TID   ÖVANDE   MARK   LUFT
    MÅNDAG 13      JFK      Inre   R8
    0800-2400

Stödjer datumformat: YYYY-MM-DD, YYYYMMDD, YYYY.MM.DD i DATUM-raden.
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

# Detektering: "VECKA : N" (eller "VECKA : N -- M") följt av "DATUM :"
VECKA_DATUM_RE = re.compile(r"VECKA\s*:\s*\d+(?:\s*--\s*\d+)?\s+DATUM\s*:", re.IGNORECASE)

# Flexibel datumintervall efter "DATUM :"
DATE_RANGE_RE = re.compile(
    r"DATUM\s*:\s*"
    r"(\d{4}[-.]?\d{2}[-.]?\d{2})"  # startdatum
    r"\s*[-–]+\s*"
    r"(\d{4}[-.]?\d{2}[-.]?\d{2})",  # slutdatum
    re.IGNORECASE,
)


def _parse_date(s: str) -> date:
    """Parsar datum i formaten YYYY-MM-DD, YYYYMMDD, YYYY.MM.DD."""
    clean = s.replace("-", "").replace(".", "")
    if len(clean) == 8:
        return date(int(clean[:4]), int(clean[4:6]), int(clean[6:8]))
    raise ValueError(f"Kan inte parsa datum: {s}")


class StandardWeeklyParser(PDFParser):
    """Parser för veckoschema med VECKA : N DATUM : start -- slut."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(VECKA_DATUM_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        match = DATE_RANGE_RE.search(text)
        if not match:
            return []

        start_date = _parse_date(match.group(1))
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        lines = text.split("\n")

        current_day_offset: int | None = None
        for line in lines:
            line_lower = line.lower().strip()

            # Kolla om raden börjar med en veckodag
            for day_name, offset in WEEKDAY_OFFSETS.items():
                if line_lower.startswith(day_name):
                    current_day_offset = offset
                    break

            if current_day_offset is None:
                continue

            # Hitta tidsintervall på denna rad
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
