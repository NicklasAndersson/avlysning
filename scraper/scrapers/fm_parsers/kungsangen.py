"""Parser för Kungsängens skjutfält (skannade tillträdesförbuds-PDF:er).

Kännetecken (efter OCR):
    KUNGSÄNGENS SKJUTFÄLT
    TILLTRADESFORBUD
    Onsdag 2026-05-06
    Kl 09.00 – 24.00

Varje PDF listar typiskt en eller flera dagar med "Veckodag YYYY-MM-DD"
följt av en rad som börjar med "Kl HH.MM – HH.MM" (eller HH:MM).
OCR-resultatet är ofta brusigt — vi tolererar valfri whitespace/skräp
mellan datum och tidsrad samt vanliga OCR-misstag i "Kl"-prefixet
(t.ex. "KI", "KL", "K1").
"""

import re
from datetime import date

from .base_parser import PDFParser

# Datumrad: ev. veckodag + ISO-datum
DATE_LINE_RE = re.compile(
    r"(?:m[åa]ndag|tisdag|onsdag|torsdag|fredag|l[öo]rdag|s[öo]ndag)?\s*"
    r"(20\d{2})-(\d{2})-(\d{2})",
    re.IGNORECASE,
)

# Tidsrad: "Kl HH.MM – HH.MM" — tolerera OCR-skräp i "Kl"-prefixet
TIME_LINE_RE = re.compile(
    r"K[lI1L]\s*(\d{1,2})[.:](\d{2})\s*[-–—]\s*(\d{1,2})[.:](\d{2})",
)

KUNGSANGEN_HEADER_RE = re.compile(
    r"KUNGS[ÄA]NGENS\s+SKJUTF[ÄA]LT",
    re.IGNORECASE,
)


class KungsangenParser(PDFParser):
    """Parser för Kungsängens tillträdesförbuds-PDF:er (OCR-tolkade)."""

    @staticmethod
    def can_parse(text: str) -> bool:
        return bool(KUNGSANGEN_HEADER_RE.search(text))

    @staticmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        restrictions: list[dict] = []
        # Hitta alla datum med position
        date_matches = list(DATE_LINE_RE.finditer(text))
        if not date_matches:
            return []

        for i, dm in enumerate(date_matches):
            year, month, day = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
            try:
                d = date(year, month, day)
            except ValueError:
                continue

            # Sök efter tidsrad i texten mellan detta datum och nästa
            window_end = date_matches[i + 1].start() if i + 1 < len(date_matches) else len(text)
            window = text[dm.end():window_end]
            tm = TIME_LINE_RE.search(window)
            if not tm:
                continue

            h1, m1, h2, m2 = (int(tm.group(j)) for j in range(1, 5))
            if not (0 <= h1 <= 24 and 0 <= h2 <= 24 and 0 <= m1 < 60 and 0 <= m2 < 60):
                continue

            restrictions.append({
                "date": d.isoformat(),
                "start": f"{h1:02d}:{m1:02d}",
                "end": f"{h2:02d}:{m2:02d}",
                "type": "tilltradesforbud",
                "sectors": ["all"],
            })

        # Deduplicera (samma datum+tider kan dyka upp flera gånger pga OCR)
        seen: set[tuple[str, str, str]] = set()
        unique: list[dict] = []
        for r in restrictions:
            key = (r["date"], r["start"], r["end"])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique
