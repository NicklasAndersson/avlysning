"""Parser för Skillingaryd-formatet: MM-DD + veckodag + tid + sektor.

Kännetecken:
    TILLTRÄDESFÖRBUD v 612
    Skillingaryds skjutfält
    Vecka Datum Dag Tid Avlyst område
    12 03-16 Mån 00.00 – 24.00 1-2
    12 03-17 Tis 00.00 – 24.00 1-2
    12 03-18 Ons 00.00 – 24.00 1 från kl 09.00
    12 03-19 Tors 00.00 – 16.30 1
"""

import re
from datetime import date

from .base_parser import PDFParser, detect_type, format_time

# Detektering: "Avlyst område" + MM-DD + veckodag + tid
_AVLYST_RE = re.compile(r"Avlyst\s+område", re.IGNORECASE)

# Rad: [vecka] MM-DD veckodag HH.MM – HH.MM [sektor] [extra]
_ROW_RE = re.compile(
    r"(?:\d{1,2}\s+)?"                                 # valfritt veckonummer
    r"(\d{2})-(\d{2})"                                 # MM-DD
    r"\s+(?:Mån|Tis|Ons|Tors?|Fre|Lör|Sön)\w*"        # veckodag
    r"\s+(\d{2})[.:](\d{2})\s*[-–]\s*(\d{2})[.:](\d{2})",  # tid
    re.IGNORECASE,
)


class SkillingarydParser(PDFParser):
    """Parser för Skillingaryd-format: MM-DD dag tid sektor."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(_AVLYST_RE.search(text)) and bool(_ROW_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        year = _extract_year(text, filename)

        for m in _ROW_RE.finditer(text):
            month = int(m.group(1))
            day = int(m.group(2))
            try:
                target_date = date(year, month, day)
            except ValueError:
                continue
            start = format_time(m.group(3), m.group(4))
            end = format_time(m.group(5), m.group(6))

            # Extrahera sektor från resten av raden
            line_end = text.find("\n", m.end())
            rest = text[m.end():line_end].strip() if line_end > 0 else ""
            sectors = _parse_sectors(rest)

            restrictions.append({
                "date": target_date.isoformat(),
                "start": start,
                "end": end,
                "type": restriction_type,
                "sectors": sectors,
            })

        restrictions.sort(key=lambda r: (r["date"], r["start"]))
        return restrictions


def _extract_year(text: str, filename: str) -> int:
    """Extrahera år från filnamn eller text."""
    m = re.search(r"20\d{2}", filename)
    if m:
        return int(m.group())
    m = re.search(r"20\d{2}", text)
    if m:
        return int(m.group())
    return date.today().year


def _parse_sectors(text: str) -> list[str]:
    """Extrahera sektorer/områden."""
    if not text:
        return ["all"]
    # Ta bort "från kl XX.XX" och liknande
    text = re.sub(r"från\s+kl\s+\d{2}[.:]\d{2}", "", text, flags=re.IGNORECASE).strip()
    m = re.match(r"^([\d][\d\s,–-]*\d?)", text)
    if m:
        raw = m.group(1).strip().replace(" ", "").replace("–", "-")
        return [raw] if raw else ["all"]
    return ["all"]
