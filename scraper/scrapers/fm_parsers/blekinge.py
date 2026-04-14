"""Parser för Blekinge-format med svenska månadsdatum.

Kännetecken:
    BLEKINGESKÄRGÅRDS ÖVNINGSFÄLT
    VECKA DATUM TIDER AVSER OMRÅDE VERKSAMHET
    Måndag 13 apr 0700-2400 Grebbegården, K-na inre öar, Soldatutbildning

Hanterar även varianter:
    Mån. 13 apr 13:00-24:00  (Ravlunda, Rinkaby — förkortade veckodagar, HH:MM-tider)
    Måndag 13 apr 08.00-22.00  (Såtenäs — HH.MM-tider med sektorer)
    TISDAG 14-apr 09.00-22.00  (Kungsängen — DD-mon med bindestreck)

Året hämtas från filnamnet (t.ex. v15-v16-2026.pdf) eller PDF-texten.
"""

import re
from datetime import date

from .base_parser import PDFParser, SWEDISH_MONTHS, detect_type

# Detektering: "VECKA DATUM TIDER" (utan kolon — skiljer från standard_weekly)
BLEKINGE_HEADER_RE = re.compile(r"VECKA\s+DATUM\s+TIDER", re.IGNORECASE)

# Rader: "[Veckodag] DD[-]mon HH[.:?]MM-HH[.:?]MM"
# Stödjer: "Måndag 13 apr 0700-2400", "Mån. 13 apr 13:00-24:00",
#          "TISDAG 14-apr 09.00-22.00", "Måndag 13 apr 08.00-22.00"
WEEKDAY_PREFIX = (
    r"(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag"
    r"|Mån\.?|Tis\.?|Ons\.?|Tor[s]?\.?|Fre\.?|Lör\.?|Sön\.?)\s*"
)
MONTH_PATTERN = (
    r"(?:jan(?:uari)?|feb(?:ruari)?|mars?|apr(?:il)?|maj"
    r"|jun[i]?|jul[i]?|aug(?:usti)?|sep(?:tember)?"
    r"|okt(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
BLEKINGE_ROW_RE = re.compile(
    WEEKDAY_PREFIX + r"?"
    r"(\d{1,2})\s*[-]?\s*"
    r"(" + MONTH_PATTERN + r")\s+"
    r"(\d{2})[.:]?(\d{2})\s*[-–]\s*(\d{2})[.:]?(\d{2})",
    re.IGNORECASE,
)


def _extract_year(filename: str, text: str) -> int:
    """Extraherar år från filnamn eller text."""
    m = re.search(r"20\d{2}", filename)
    if m:
        return int(m.group())
    m = re.search(r"20\d{2}", text)
    if m:
        return int(m.group())
    return date.today().year


class BlekingeParser(PDFParser):
    """Parser för Blekinge-format med 'Måndag 13 apr 0700-2400'."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(BLEKINGE_HEADER_RE.search(text)) or bool(BLEKINGE_ROW_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        year = _extract_year(filename, text)
        restriction_type = detect_type(text)
        restrictions: list[dict] = []

        for match in BLEKINGE_ROW_RE.finditer(text):
            day_num = int(match.group(1))
            # Normalisera månad till kort form för uppslagning
            raw_month = match.group(2).lower()
            if raw_month.startswith("mar"):
                raw_month = "mar"
            elif raw_month.startswith("jun"):
                raw_month = "jun"
            elif raw_month.startswith("jul"):
                raw_month = "jul"
            elif len(raw_month) > 3:
                raw_month = raw_month[:3]
            month = SWEDISH_MONTHS.get(raw_month)
            if not month:
                continue

            h1, m1 = match.group(3), match.group(4)
            h2, m2 = match.group(5), match.group(6)
            # Grupp 2 kan vara fångande pga MONTH_PATTERN — justera gruppindex
            # Grupp 1=dag, 2=månad, 3-6=tid

            try:
                d = date(year, month, day_num)
            except ValueError:
                continue

            # Försök extrahera sektorer efter tidsintervallet
            line_end = text.find("\n", match.end())
            rest_of_line = text[match.end():line_end].strip() if line_end > 0 else ""
            sectors = ["all"]
            if rest_of_line:
                # Sektorer som "5, 6, 7 + 13" eller "a-c-d-h"
                sector_match = re.match(r"^[\s]*([\d\w,+\- ]+)", rest_of_line)
                if sector_match:
                    raw = sector_match.group(1).strip()
                    # Filtrera bort om det ser ut som beskrivande text
                    if len(raw) < 40 and not re.search(r"[a-zåäö]{4,}", raw, re.IGNORECASE):
                        parts = re.split(r"[,+]\s*", raw)
                        sectors = [s.strip() for s in parts if s.strip()]

            restrictions.append({
                "date": d.isoformat(),
                "start": f"{int(h1):02d}:{int(m1):02d}",
                "end": f"{int(h2):02d}:{int(m2):02d}",
                "type": restriction_type,
                "sectors": sectors if sectors else ["all"],
            })

        return restrictions
