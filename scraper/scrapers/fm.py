"""Scraper för Försvarsmaktens skjutfält och avlysningar via deras interna API."""

import io
import json
import re
from pathlib import Path

import pdfplumber

from .base import BaseScraper
from .fm_parsers import parse_pdf_text

# FM:s interna API som returnerar alla skjutfält med PDF-länkar
FM_API_URL = "https://www.forsvarsmakten.se/api/searchapi/get-firing-ranges?lang=sv"
FM_BASE_URL = "https://www.forsvarsmakten.se"
PAGE_SIZE = 12  # API returnerar 12 resultat per sida


class FMScraper(BaseScraper):
    """Scrapar avlysnings-PDF:er från forsvarsmakten.se via deras JSON API."""

    def scrape(self) -> list[dict]:
        """Hämtar alla skjutfält via API:et och laddar ner relevanta PDF:er."""
        # Ladda field_config för statisk parsertilldelning
        config_path = Path(__file__).parent.parent.parent / "data" / "field_config.json"
        field_config: dict[str, dict] = {}
        if config_path.exists():
            field_config = json.loads(config_path.read_text(encoding="utf-8")).get("fields", {})
            self.logger.info("Laddade field_config med %d fält från %s", len(field_config), config_path)
        else:
            self.logger.warning("field_config.json hittades inte på %s — inga parsers tilldelas!", config_path)

        fields: list[dict] = []
        all_ranges = self._get_all_ranges()
        self.logger.info("Hittade %d skjutfält via API:et", len(all_ranges))

        for range_data in all_ranges:
            try:
                heading = range_data.get("heading", "")
                parser_name = field_config.get(heading, {}).get("parser")
                field = self._process_range(range_data, parser_name)
                if field:
                    fields.append(field)
            except Exception:
                self.logger.exception(
                    "Kunde inte bearbeta fält: %s", range_data.get("heading", "Okänt")
                )

        return fields

    def _get_all_ranges(self) -> list[dict]:
        """Hämtar alla skjutfält från FM:s API med paginering (skip-parameter)."""
        all_ranges: list[dict] = []
        skip = 0

        while True:
            url = f"{FM_API_URL}&skip={skip}" if skip > 0 else FM_API_URL
            resp = self.fetch(url, ttl=0)
            data = resp.json()

            results = data.get("results", [])
            if not results:
                break

            all_ranges.extend(results)
            total = data.get("totalMatching", 0)

            skip += PAGE_SIZE
            if skip >= total:
                break

            # Säkerhetsgräns
            if skip > 200:
                self.logger.warning("Avbryter paginering vid skip=%d", skip)
                break

        return all_ranges

    def _process_range(self, range_data: dict, parser_name: str | None = None) -> dict | None:
        """Bearbetar ett skjutfält: filtrera PDF:er, ladda ner och parsa.

        Alla dokument under en heading tillhör det fältet — ingen gissning
        utifrån filnamn behövs.
        """
        heading = range_data.get("heading", "Okänt fält")
        documents = range_data.get("documents") or []

        if not documents:
            self.logger.debug("Inga dokument för %s", heading)
            return None

        field_id = self._make_id(heading)

        # Filtrera avlysnings-PDF:er (inte kartor etc)
        restriction_docs = [
            d for d in documents
            if any(kw in d.get("title", "").lower()
                   for kw in ["tilltradesforbud", "skjutvarning", "avlysning", "varningsmeddelande"])
        ]

        # Om inga specifika, ta alla icke-karta PDF:er
        if not restriction_docs:
            restriction_docs = [
                d for d in documents
                if "karta" not in d.get("title", "").lower()
                and d.get("url", "").lower().endswith(".pdf")
            ]

        self.logger.info(
            "Fält '%s': %d avlysnings-PDF:er av %d dokument",
            heading, len(restriction_docs), len(documents),
        )

        restrictions: list[dict] = []
        pdf_urls: list[str] = []
        for doc in restriction_docs:
            pdf_url = FM_BASE_URL + doc["url"]
            pdf_urls.append(pdf_url)
            try:
                pdf_restrictions = self._parse_pdf(pdf_url, parser_name)
                for r in pdf_restrictions:
                    r["source_url"] = pdf_url
                restrictions.extend(pdf_restrictions)
            except Exception:
                self.logger.exception("Kunde inte parsa PDF: %s", pdf_url)

        # Deduplicera (samma datum+tid+typ+sektorer)
        seen: set[tuple[str, ...]] = set()
        unique: list[dict] = []
        for r in restrictions:
            key = (r["date"], r.get("start", ""), r.get("end", ""),
                   r["type"], tuple(r["sectors"]))
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return {
            "id": field_id,
            "name": heading,
            "source": "forsvarsmakten.se",
            "source_url": pdf_urls[0] if pdf_urls else
                FM_BASE_URL + "/regler-och-tillstand/skjutfalt-och-forbud/",
            "restrictions": unique,
        }

    def _parse_pdf(self, pdf_url: str, parser_name: str | None = None) -> list[dict]:
        """Laddar ner och parsar en avlysnings-PDF via konfigurerad parser."""
        pdf_bytes = self.fetch_bytes(pdf_url)
        filename = pdf_url.split("/")[-1]

        try:
            full_text = self._extract_pdf_text(pdf_bytes, filename)
        except Exception as e:
            self.logger.warning("Kunde inte läsa PDF %s: %s", filename, e)
            # Radera cachad PDF vid läsfel, kan vara korrupt
            self._delete_cache(pdf_url)
            return []

        if not full_text.strip():
            self.logger.warning("Tom PDF (ingen text): %s", pdf_url)
            # Radera cachad PDF utan text så vi försöker igen nästa körning
            self._delete_cache(pdf_url)
            return []

        restrictions = parse_pdf_text(full_text, filename, parser_name=parser_name)
        if restrictions is None:
            self.logger.warning("Ingen parser matchade: %s", filename)
            return []
        self.logger.info(
            "PDF %s: %d restriktioner", filename, len(restrictions)
        )
        return restrictions

    @staticmethod
    def _extract_pdf_text(pdf_bytes: bytes, filename: str, timeout: int = 30) -> str:
        """Extraherar text från PDF-bytes."""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            parts: list[str] = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
        return "\n".join(parts)

    @staticmethod
    def _make_id(name: str) -> str:
        """Skapar ett URL-vänligt ID från fältnamn."""
        import unicodedata
        # Normalisera och ta bort accenter
        nfkd = unicodedata.normalize("NFKD", name.lower())
        ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
        # Ersätt icke-alfanumeriska med bindestreck
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
        return slug
