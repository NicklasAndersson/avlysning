"""Basmodul för PDF-formatparsers med gemensamma hjälpfunktioner."""

import re
from abc import ABC, abstractmethod


# Gemensamma regex-mönster
TIME_RANGE_RE = re.compile(r"(\d{2})[.:]?(\d{2})\s*[-–]\s*(\d{2})[.:]?(\d{2})")

WEEKDAY_OFFSETS: dict[str, int] = {
    "måndag": 0, "mandag": 0,
    "tisdag": 1,
    "onsdag": 2,
    "torsdag": 3,
    "fredag": 4,
    "lördag": 5, "lordag": 5,
    "söndag": 6, "sondag": 6,
}

SWEDISH_MONTHS: dict[str, int] = {
    "jan": 1, "januari": 1,
    "feb": 2, "februari": 2,
    "mar": 3, "mars": 3,
    "apr": 4, "april": 4,
    "maj": 5,
    "jun": 6, "juni": 6,
    "jul": 7, "juli": 7,
    "aug": 8, "augusti": 8,
    "sep": 9, "september": 9,
    "okt": 10, "oktober": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


class PDFParser(ABC):
    """Abstrakt basklass för PDF-formatparsers."""

    @staticmethod
    @abstractmethod
    def can_parse(text: str) -> bool:
        """Returnerar True om denna parser kan hantera texten."""
        ...

    @staticmethod
    @abstractmethod
    def parse(text: str, filename: str = "") -> list[dict]:
        """Parsar PDF-text och returnerar lista med restriktioner."""
        ...


def detect_type(text: str) -> str:
    """Detekterar restriktionstyp (tilltradesforbud eller skjutvarning) från PDF-text."""
    upper = text.upper()
    if "TILLTRÄDESFÖRBUD" in upper or "TILLTRADESFORBUD" in upper:
        return "tilltradesforbud"
    return "skjutvarning"


def format_time(h: str, m: str) -> str:
    """Formaterar timme och minut till HH:MM."""
    return f"{int(h):02d}:{int(m):02d}"
