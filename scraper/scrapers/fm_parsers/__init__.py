"""PDF-formatparser-registret. Detekterar rätt parser för varje PDF.

Parsers provas i prioritetsordning — mer specifika format först.
"""

import logging
import re

from .amf1 import Amf1Parser
from .beslut import BeslutParser
from .blekinge import BlekingeParser
from .date_slash import DateSlashParser
from .generic_iso import GenericIsoParser
from .harnosand import HarnosandParser
from .marma import MarmaParser
from .standard_weekly import StandardWeeklyParser
from .tame import TameParser
from .yy_mm_dd import YyMmDdParser

logger = logging.getLogger(__name__)

# Regex för att detektera "ingen farlig verksamhet"-PDFer
NO_ACTIVITY_RE = re.compile(
    r"ingen\s+farlig\s+verksamhet\s+planerad",
    re.IGNORECASE,
)

# Prioritetsordning: specifika parsers först, generella sist
PARSERS: list[tuple[str, type]] = [
    ("tame", TameParser),
    ("marma", MarmaParser),
    ("harnosand", HarnosandParser),
    ("blekinge", BlekingeParser),
    ("beslut", BeslutParser),
    ("amf1", Amf1Parser),
    ("standard_weekly", StandardWeeklyParser),
    ("yy_mm_dd", YyMmDdParser),
    ("date_slash", DateSlashParser),
    ("generic_iso", GenericIsoParser),
]


def parse_pdf_text(text: str, filename: str = "") -> list[dict] | None:
    """Detekterar format och parsar PDF-text till restriktioner.

    Returnerar None om ingen parser matchade (skiljer från tom lista
    som betyder att parsern matchade men inga restriktioner hittades).
    """
    # Snabbkontroll: "Ingen farlig verksamhet planerad" → tomt resultat
    if NO_ACTIVITY_RE.search(text):
        logger.info("Inga restriktioner (ingen farlig verksamhet): %s", filename)
        return []

    for name, parser_cls in PARSERS:
        if parser_cls.can_parse(text):
            logger.info("Använder parser '%s' för %s", name, filename or "(okänd)")
            return parser_cls.parse(text, filename)

    logger.warning("Ingen parser matchade för %s", filename or "(okänd)")
    return None
