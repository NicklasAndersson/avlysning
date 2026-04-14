"""Parser för generiskt ISO-datumformat (YYYY-MM-DD + tidsintervall).

Hanterar PDF:er där varje rad har ett fullständigt ISO-datum följt av tid.
Stödjer varianter:

    2026-04-13 Måndag 0800-2400            (Remmene, Sågebacken)
    * 2026-04-13 * Måndag 0800-2400        (Remmene med asterisker)
    2026-04-14 08.00-24.00 a-c-d-h*        (Falun — utan veckodag)
    2026-04-14 Tisdag 616 0900-1600 2,4,5  (Prästtomta — med veckonummer)
    2026-04-15 Onsdag 07:00-00:00          (Sisjön)
    Måndag 2026-04-13 JA 0800-2400         (Umeå — veckodag före datum)

Detekteras genom att YYYY-MM-DD-datum INTE föregås av "Beslut" + FM-referens
(det hanteras av beslut.py).
"""

import re

from .base_parser import PDFParser, TIME_RANGE_RE, detect_type, format_time

# ISO-datum som fristående token (inte del av FM-referens)
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

# Rad med ISO-datum + tidsintervall (valfritt mellanliggande text)
ISO_ROW_RE = re.compile(
    r"\*?\s*(\d{4}-\d{2}-\d{2})\s*\*?\s+"
    r"(?:(?:[A-Za-zÅÄÖåäö.]+|\d+)\s+)*?"  # valfritt: veckodag, veckonummer, JA/NEJ
    r"(\d{2})[.:]?(\d{2})\s*[-–]\s*(\d{2})[.:]?(\d{2})"
)

# Alternativ: veckodag FÖRE iso-datum (Umeå-format)
WEEKDAY_ISO_ROW_RE = re.compile(
    r"(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)\s+"
    r"(\d{4}-\d{2}-\d{2})\s+"
    r"(?:JA|NEJ)?\s*"
    r"(\d{2})[.:]?(\d{2})\s*[-–]\s*(\d{2})[.:]?(\d{2})",
    re.IGNORECASE,
)

# Beslut-format exkluderas (hanteras av beslut.py)
BESLUT_RE = re.compile(r"^Beslut\s*$", re.MULTILINE)
FM_REF_RE = re.compile(r"FM20\d{2}-\d+:\d+")


class GenericIsoParser(PDFParser):
    """Parser för PDF:er med ISO-datum (YYYY-MM-DD) och tidsintervall."""

    @staticmethod
    def can_parse(text: str) -> bool:
        # Har ISO-datum med tidsintervall men är inte ett Beslut-dokument
        if BESLUT_RE.search(text) and FM_REF_RE.search(text):
            return False
        has_rows = bool(ISO_ROW_RE.search(text)) or bool(WEEKDAY_ISO_ROW_RE.search(text))
        return has_rows

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        seen: set[tuple[str, str, str]] = set()

        for pattern in [ISO_ROW_RE, WEEKDAY_ISO_ROW_RE]:
            for match in pattern.finditer(text):
                date_str = match.group(1)
                h1, m1 = match.group(2), match.group(3)
                h2, m2 = match.group(4), match.group(5)

                start = format_time(h1, m1)
                end = format_time(h2, m2)
                key = (date_str, start, end)
                if key in seen:
                    continue
                seen.add(key)

                # Försök extrahera sektorer efter tidsintervallet
                line_end = text.find("\n", match.end())
                rest_of_line = text[match.end():line_end].strip() if line_end > 0 else ""
                sectors = _extract_sectors(rest_of_line)

                restrictions.append({
                    "date": date_str,
                    "start": start,
                    "end": end,
                    "type": restriction_type,
                    "sectors": sectors,
                })

        restrictions.sort(key=lambda r: (r["date"], r["start"]))
        return restrictions


def _extract_sectors(rest: str) -> list[str]:
    """Extraherar sektorer/områden från resten av raden."""
    if not rest:
        return ["all"]

    # Ta bort asterisker och kända icke-sektor-ord
    rest = rest.strip("* ")
    skip_words = {"ingen", "avlysning", "skarpskjutning", "lysskjutning",
                  "soldatutbildning", "övning", "högt", "buller"}
    if any(w in rest.lower() for w in skip_words):
        return ["all"]

    # Sektorer som "2,4,5" eller "a-c-d-h" eller "5, 6, 7 + 13"
    if re.match(r"^[\dA-Za-z,+\-\s]+$", rest) and len(rest) < 40:
        parts = re.split(r"[,+]\s*", rest)
        sectors = [s.strip() for s in parts if s.strip()]
        if sectors:
            return sectors

    return ["all"]
