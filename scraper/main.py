#!/usr/bin/env python3
"""
FM Avlysning — Scraper

Scrapar avlysningar från Försvarsmakten, skjutfalten.se och kommunsidor.
Genererar skjutfalt_status.json med normaliserad data.
"""

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from scrapers.fm import FMScraper
from scrapers.bofors import BoforsScraper
from scrapers.kommun import KommunScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fm-avlysning")

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "skjutfalt_status.json"

# Minsta fördröjning mellan HTTP-anrop (sekunder)
REQUEST_DELAY = 2.0

USER_AGENT = "FM-Avlysning-Scraper/0.1 (https://github.com/fm-avlysning; kontakt@example.com)"


def merge_results(all_fields: list[dict]) -> dict:
    """Slår ihop resultat från alla scrapers till ett enhetligt JSON-dokument."""
    return {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fields": all_fields,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrapa avlysningar för skjutfält")
    parser.add_argument(
        "--source",
        choices=["fm", "bofors", "kommun", "all"],
        default="all",
        help="Vilken källa som ska scrapas (default: all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_FILE,
        help="Sökväg till output-fil (default: data/skjutfalt_status.json)",
    )
    args = parser.parse_args()

    all_fields: list[dict] = []

    scrapers = {
        "fm": FMScraper,
        "bofors": BoforsScraper,
        "kommun": KommunScraper,
    }

    sources = list(scrapers.keys()) if args.source == "all" else [args.source]

    for source_name in sources:
        logger.info("Startar scraping av: %s", source_name)
        try:
            scraper = scrapers[source_name](
                user_agent=USER_AGENT,
                delay=REQUEST_DELAY,
            )
            fields = scraper.scrape()
            all_fields.extend(fields)
            logger.info("Klart: %s — %d fält hämtade", source_name, len(fields))
        except Exception:
            logger.exception("Fel vid scraping av %s", source_name)

    result = merge_results(all_fields)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Resultat sparat till %s (%d fält totalt)", args.output, len(all_fields))


if __name__ == "__main__":
    main()
