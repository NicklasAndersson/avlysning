"""Parser för Tofta-format med datumintervall (tillträdesförbud + öppet för allmänheten).

Kännetecken:
    TILLTRÄDESFÖRBUD ÖPPET FÖR ALLMÄNHETEN
    Till                   Till
    Datum Dag Tid och med  Datum Dag Tid

    Rader med dubbla datum:
    2026-04-06 Måndag 07:00 2026-04-17 Fredag 16:30
"""

import re
from datetime import date, timedelta

from .base_parser import PDFParser, detect_type

# Detektering: "ÖPPET FÖR ALLMÄNHETEN" i kombination med datumintervall
OPEN_FOR_PUBLIC_RE = re.compile(r"ÖPPET\s+FÖR\s+ALLMÄNHETEN", re.IGNORECASE)

# Matchar en rad med två datum-tid-par:
# 2026-04-06 Måndag 07:00 2026-04-17 Fredag 16:30
DUAL_DATE_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s+"
    r"(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)\s+"
    r"(\d{2})[.:](\d{2})\s+"
    r"(\d{4}-\d{2}-\d{2})\s+"
    r"(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)\s+"
    r"(\d{2})[.:](\d{2})",
    re.IGNORECASE,
)


def _expand_range(
    start_date: str,
    start_h: str,
    start_m: str,
    end_date: str,
    end_h: str,
    end_m: str,
    restriction_type: str,
) -> list[dict]:
    """Expanderar ett datumintervall till enskilda dagsrestriktioner."""
    d_start = date.fromisoformat(start_date)
    d_end = date.fromisoformat(end_date)
    s_time = f"{int(start_h):02d}:{int(start_m):02d}"
    e_time = f"{int(end_h):02d}:{int(end_m):02d}"

    restrictions: list[dict] = []
    d = d_start
    while d <= d_end:
        if d == d_start and d == d_end:
            day_start, day_end = s_time, e_time
        elif d == d_start:
            day_start, day_end = s_time, "23:59"
        elif d == d_end:
            day_start, day_end = "00:00", e_time
        else:
            day_start, day_end = "00:00", "23:59"

        restrictions.append({
            "date": d.isoformat(),
            "start": day_start,
            "end": day_end,
            "type": restriction_type,
            "sectors": ["all"],
        })
        d += timedelta(days=1)

    return restrictions


class ToftaParser(PDFParser):
    """Parser för Tofta-format med datumintervall (tillträdesförbud/öppet)."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(OPEN_FOR_PUBLIC_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        matches = list(DUAL_DATE_RE.finditer(text))

        if not matches:
            return []

        # Raderna alternerar: jämna index (0, 2, 4, ...) = tillträdesförbud,
        # udda index (1, 3, 5, ...) = öppet för allmänheten.
        # Vi tar bara restriktionsraderna.
        restrictions: list[dict] = []
        for i, match in enumerate(matches):
            if i % 2 != 0:
                continue  # Hoppa över "öppet för allmänheten"-rader
            restrictions.extend(
                _expand_range(
                    match.group(1),
                    match.group(2),
                    match.group(3),
                    match.group(4),
                    match.group(5),
                    match.group(6),
                    restriction_type,
                )
            )

        return restrictions
