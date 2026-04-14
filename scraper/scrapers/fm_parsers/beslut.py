"""Parser för formellt beslutsformat (Revingehed, Romeleklint).

Kännetecken:
    Beslut
    Datum Beteckning
    2026-02-17 FM2025-28767:16
    ...
    Datum Klockslag Områden Övningsledare
    2026-03-10 0900-2400 B1-B4 PBat
"""

import re

from .base_parser import PDFParser, detect_type, format_time

# Detektering: "Beslut" som egen rad + FM-referens
BESLUT_RE = re.compile(r"^Beslut\s*$", re.MULTILINE)
FM_REF_RE = re.compile(r"FM20\d{2}-\d+:\d+")

# Datumrader: "2026-03-10 0900-2400 ..."
DATE_TIME_ROW_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s+"
    r"(\d{2})(\d{2})\s*[-–]\s*(\d{2})(\d{2})"
)


class BeslutParser(PDFParser):
    """Parser för formella beslutsdokument med ISO-datumtabell."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(BESLUT_RE.search(text)) and bool(FM_REF_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []

        for match in DATE_TIME_ROW_RE.finditer(text):
            date_str = match.group(1)
            h1, m1 = match.group(2), match.group(3)
            h2, m2 = match.group(4), match.group(5)

            # Försök extrahera sektorer/områden efter tidsintervallet
            line_end = text.find("\n", match.end())
            rest_of_line = text[match.end():line_end].strip() if line_end > 0 else ""
            sectors = ["all"]
            if rest_of_line:
                sectors_match = re.match(r"([A-Z0-9][A-Za-z0-9,\- ]+)", rest_of_line)
                if sectors_match:
                    sector_text = sectors_match.group(1).strip()
                    if re.match(r"^[A-Z0-9,\- ]+$", sector_text):
                        sectors = [s.strip() for s in sector_text.split(",") if s.strip()]

            restrictions.append({
                "date": date_str,
                "start": format_time(h1, m1),
                "end": format_time(h2, m2),
                "type": restriction_type,
                "sectors": sectors if sectors else ["all"],
            })

        return restrictions
