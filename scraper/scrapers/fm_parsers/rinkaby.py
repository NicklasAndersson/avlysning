"""Parser för Rinkaby/Pansarövningsfältet: prosa-datumspann på svenska.

Kännetecken:
    Pansarövningsfältet Rinkaby (pöf)
    Torsdag 5 mars kl:14:00 till måndag 9 mars kl:10:00
    Måndag 30 mars kl: 09:00 till tisdag 31 mars 24:00.
    Onsdag 1 april KL 00:00 till måndag 20 april KL 12:00

Varje rad beskriver ett tidsintervall som kan sträcka sig över flera dagar.
Expanderas till dagliga restriktioner.
"""

import re
from datetime import date, timedelta

from .base_parser import PDFParser, SWEDISH_MONTHS, detect_type

# Detektering
_RINKABY_RE = re.compile(
    r"Pansarövningsfältet|Rinkaby\s+Skjutfält",
    re.IGNORECASE,
)
_KL_TILL_RE = re.compile(r"kl\s*:?\s*\d{1,2}:\d{2}\s+till", re.IGNORECASE)

# Datumspann: veckodag D(D) månad kl(:|) HH:MM till veckodag D(D) månad (kl(:|))? HH:MM
_SPAN_RE = re.compile(
    r"(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)\s+"
    r"(\d{1,2})\s+"                          # startdag
    r"(\w+)\s+"                              # startmånad
    r"(?:kl\s*:?\s*)"                        # kl-prefix
    r"(\d{1,2}):(\d{2})"                     # starttid
    r"\s+till\s+"
    r"(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)\s+"
    r"(\d{1,2})\s+"                          # slutdag
    r"(\w+)\s+"                              # slutmånad
    r"(?:kl\s*:?\s*)?"                       # kl-prefix (valfritt)
    r"(\d{1,2}):(\d{2})",                    # sluttid
    re.IGNORECASE,
)


class RinkabyParser(PDFParser):
    """Parser för Rinkaby/Pansarövningsfältet: prosa-datumspann."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(_RINKABY_RE.search(text)) and bool(_KL_TILL_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restriction_type = detect_type(text)
        restrictions: list[dict] = []
        year = _extract_year(text, filename)

        for m in _SPAN_RE.finditer(text):
            start_day = int(m.group(1))
            start_month = SWEDISH_MONTHS.get(m.group(2).lower())
            start_h = int(m.group(3))
            start_m = int(m.group(4))
            end_day = int(m.group(5))
            end_month = SWEDISH_MONTHS.get(m.group(6).lower())
            end_h = int(m.group(7))
            end_m = int(m.group(8))

            if not start_month or not end_month:
                continue

            try:
                start_date = date(year, start_month, start_day)
                end_date = date(year, end_month, end_day)
            except ValueError:
                continue

            # Expandera till dagliga restriktioner
            current = start_date
            while current <= end_date:
                if current == start_date:
                    s = f"{start_h:02d}:{start_m:02d}"
                else:
                    s = "00:00"

                if current == end_date:
                    e = f"{end_h:02d}:{end_m:02d}"
                else:
                    e = "24:00"

                restrictions.append({
                    "date": current.isoformat(),
                    "start": s,
                    "end": e,
                    "type": restriction_type,
                    "sectors": ["all"],
                })
                current += timedelta(days=1)

        restrictions.sort(key=lambda r: (r["date"], r["start"]))
        return restrictions


def _extract_year(text: str, filename: str) -> int:
    """Extrahera år."""
    m = re.search(r"20\d{2}", filename)
    if m:
        return int(m.group())
    m = re.search(r"20\d{2}", text)
    if m:
        return int(m.group())
    return date.today().year
