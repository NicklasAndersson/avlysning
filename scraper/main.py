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
from upload import upload_to_r2

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
    """Slår ihop resultat från alla scrapers till ett enhetligt JSON-dokument.

    Fält med samma id slås ihop: restriktioner samlas, och extra källinfo bevaras.
    FM-källa prioriteras för namn/source_url om den finns.
    """
    merged: dict[str, dict] = {}
    for field in all_fields:
        fid = field["id"]
        if fid not in merged:
            merged[fid] = dict(field)
        else:
            existing = merged[fid]
            # Lägg till restriktioner från den nya källan
            existing.setdefault("restrictions", []).extend(
                field.get("restrictions", [])
            )
            # Behåll FM som primär källa om den finns
            if field.get("source") == "forsvarsmakten.se":
                existing["source"] = field["source"]
                existing["source_url"] = field.get("source_url", existing.get("source_url"))

    return {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fields": list(merged.values()),
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
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignorera disk-cache och hämta allt på nytt",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=86400,
        help="Cache-giltighetstid i sekunder (default: 86400 = 1 dygn)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Ladda upp resultat till R2 via S3 efter scraping (kräver S3_*-miljövariabler)",
    )
    args = parser.parse_args()

    cache_ttl = 0 if args.no_cache else args.cache_ttl

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
                cache_ttl=cache_ttl,
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

    if args.upload:
        logger.info("Laddar upp resultat till R2...")
        upload_to_r2(args.output.parent)
        logger.info("Upload klar")


if __name__ == "__main__":
    main()
