"""PDF-formatparser-registret. Detekterar rätt parser för varje PDF.

Parsers provas i prioritetsordning — mer specifika format först.
"""

import logging
import re

from .alvdalen_andring import AlvdalenAndringParser
from .amf1 import Amf1Parser
from .beslut import BeslutParser
from .blekinge import BlekingeParser
from .date_slash import DateSlashParser
from .enkoping import EnkopingParser
from .generic_iso import GenericIsoParser
from .harad import HaradParser
from .harnosand import HarnosandParser
from .kalixfors import KalixforsParser
from .karlsborg import KarlsborgParser
from .marma import MarmaParser
from .norra_asum import NorraAsumParser
from .rinkaby import RinkabyParser
from .skillingaryd import SkillingarydParser
from .skovde import SkovdeParser
from .standard_weekly import StandardWeeklyParser
from .tame import TameParser
from .yy_mm_dd import YyMmDdParser

logger = logging.getLogger(__name__)

# Regex för att detektera "ingen farlig verksamhet"-PDFer
NO_ACTIVITY_RE = re.compile(
    r"ingen\s+farlig\s+verksamhet\s+planerad",
    re.IGNORECASE,
)

# Regex för statiska informationsblad utan schemalagda datum
STATIC_INFO_RE = re.compile(
    r"Varning\s+för\s+att\s+uppehålla\s+sig"  # F7-format
    r"|Riskzon\s+i\s+Vänern"                   # Vänern riskomrade
    r"|riskomrade.*vänern"                      # Vänern variant
    r"|Detta\s+är\s+ett\s+militärt\s+övningsområde.*Visa\s+hänsyn",  # Bråt-format
    re.IGNORECASE | re.DOTALL,
)

# Regex för "alla dagar NEJ" (t.ex. Umeå med alla "NEJ Ingen avlysning")
# Matchar om det finns NEJ-rader men inga JA-rader med tidsintervall
ALL_NEJ_RE = re.compile(r"NEJ\s+Ingen\s+avlysning", re.IGNORECASE)
ANY_JA_RE = re.compile(r"JA\s+\d{2}", re.IGNORECASE)

# Regex för "inget tillträdesförbud" under perioden (explicit negation)
NO_RESTRICTION_RE = re.compile(
    r"Inget\s+tillträdesförbud",
    re.IGNORECASE,
)

# Regex för övningsinformation (ej restriktioner)
EXERCISE_INFO_RE = re.compile(
    r"ÖVNINGS\s*information",
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
    ("norra_asum", NorraAsumParser),
    ("rinkaby", RinkabyParser),
    ("enkoping", EnkopingParser),
    ("karlsborg", KarlsborgParser),
    ("kalixfors", KalixforsParser),
    ("harad", HaradParser),
    ("alvdalen_andring", AlvdalenAndringParser),
    ("skovde", SkovdeParser),
    ("skillingaryd", SkillingarydParser),
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

    # Statiska informationsblad utan schemalagda datum → tomt resultat
    if STATIC_INFO_RE.search(text):
        logger.info("Statiskt informationsblad (inga datum): %s", filename)
        return []

    # Alla dagar "NEJ Ingen avlysning" och inga JA-rader → tomt resultat
    if ALL_NEJ_RE.search(text) and not ANY_JA_RE.search(text):
        logger.info("Inga restriktioner (alla NEJ): %s", filename)
        return []

    # "Inget tillträdesförbud" / "Ingen skjutning under perioden" / "Inget riskområde"
    if NO_RESTRICTION_RE.search(text):
        logger.info("Inga restriktioner (explicit ingen avlysning): %s", filename)
        return []

    # Övningsinformation utan riskområde → inte en restriktion
    if EXERCISE_INFO_RE.search(text) and not re.search(r"riskområde\s*\d", text, re.IGNORECASE):
        logger.info("Övningsinformation (ej restriktion): %s", filename)
        return []

    for name, parser_cls in PARSERS:
        if parser_cls.can_parse(text):
            logger.info("Använder parser '%s' för %s", name, filename or "(okänd)")
            return parser_cls.parse(text, filename)

    logger.warning("Ingen parser matchade för %s", filename or "(okänd)")
    return None
