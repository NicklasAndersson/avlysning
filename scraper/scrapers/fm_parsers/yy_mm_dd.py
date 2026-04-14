"""Parser för YY-MM-DD datumformat (Eksjö, Villingsberg).

Kännetecken:
    Lördag 26-04-18 0730-1630 Enligt karta      (Eksjö)
    616 Måndag 26-04-13 07:00-24:00 2,3,4,5,5A,8 (Villingsberg)

Datumen har tvåsiffrigt årtal (26-04-18 = 2026-04-18).
"""

import re

from .base_parser import PDFParser, detect_type, format_time

# YY-MM-DD datum (tvåsiffrigt år, t.ex. 26-04-13)
YY_DATE_RE = re.compile(
    r"(\d{2})-(\d{2})-(\d{2})\s+"
    r"(\d{2})[.:]?(\d{2})\s*[-–]\s*(\d{2})[.:]?(\d{2})"
)

# Detektering: minst en rad med YY-MM-DD + tid
DETECT_RE = re.compile(r"\b\d{2}-\d{2}-\d{2}\s+\d{2}[.:]?\d{2}\s*[-–]")


class YyMmDdParser(PDFParser):
    """Parser för PDF:er med YY-MM-DD datumformat."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(DETECT_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []

        for match in YY_DATE_RE.finditer(text):
            yy = int(match.group(1))
            mm = int(match.group(2))
            dd = int(match.group(3))
            year = 2000 + yy

            h1, m1 = match.group(4), match.group(5)
            h2, m2 = match.group(6), match.group(7)

            try:
                date_str = f"{year:04d}-{mm:02d}-{dd:02d}"
            except ValueError:
                continue

            # Extrahera sektorer efter tidsintervallet
            line_end = text.find("\n", match.end())
            rest_of_line = text[match.end():line_end].strip() if line_end > 0 else ""
            sectors = _extract_sectors(rest_of_line)

            restrictions.append({
                "date": date_str,
                "start": format_time(h1, m1),
                "end": format_time(h2, m2),
                "type": restriction_type,
                "sectors": sectors,
            })

        return restrictions


def _extract_sectors(rest: str) -> list[str]:
    """Extraherar sektorer/områden från resten av raden."""
    if not rest:
        return ["all"]
    # Ta bort "Enligt karta" och liknande
    if "karta" in rest.lower():
        return ["all"]
    # Sektorer som "2,3,4,5,5A,8"
    if re.match(r"^[\dA-Za-z,\s]+$", rest) and len(rest) < 40:
        parts = [s.strip() for s in rest.split(",") if s.strip()]
        if parts:
            return parts
    return ["all"]
