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
        fields: list[dict] = []
        all_ranges = self._get_all_ranges()
        self.logger.info("Hittade %d skjutfält via API:et", len(all_ranges))

        # Samla alla fält-ID:n för korsvalidering av PDF-kataloger
        all_field_ids = {self._make_id(r.get("heading", "")) for r in all_ranges}

        # Inkludera fältnamn från field_config.json (innehåller fält som saknar
        # eget API-heading men har egna polygoner, t.ex. Trelge under Tofta)
        field_config_path = Path(__file__).parent.parent.parent / "data" / "field_config.json"
        if field_config_path.exists():
            try:
                cfg = json.loads(field_config_path.read_text(encoding="utf-8"))
                for name in cfg.get("fields", {}):
                    all_field_ids.add(self._make_id(name))
            except Exception:
                self.logger.warning("Kunde inte läsa field_config.json")

        for range_data in all_ranges:
            try:
                result = self._process_range(range_data, all_field_ids)
                if result:
                    fields.extend(result)
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

    def _process_range(self, range_data: dict, all_field_ids: set[str] | None = None) -> list[dict]:
        """Bearbetar ett skjutfält: filtrera PDF:er, ladda ner och parsa.

        Returnerar en lista med fält-entries. Vanligtvis ett, men kan vara flera
        om API:et listar PDF:er för olika fält under samma heading (t.ex. Tofta + Trelge).
        """
        heading = range_data.get("heading", "Okänt fält")
        documents = range_data.get("documents") or []

        if not documents:
            self.logger.debug("Inga dokument för %s", heading)
            return []

        # Skapa ID från namn
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

        # Gruppera dokument per fält baserat på filnamn.
        # Om filnamnet nämner ett annat känt fält → tilldela dit.
        doc_groups: dict[str, list[dict]] = {}
        for doc in restriction_docs:
            target_id, target_name = self._resolve_doc_field(
                doc, field_id, heading, all_field_ids,
            )
            doc_groups.setdefault(target_id, {"name": target_name, "docs": []})
            doc_groups[target_id]["docs"].append(doc)

        # Bearbeta varje grupp till ett fält-entry
        results: list[dict] = []
        for fid, group in doc_groups.items():
            field_entry = self._build_field_entry(fid, group["name"], group["docs"])
            if field_entry:
                results.append(field_entry)

        return results

    def _resolve_doc_field(
        self, doc: dict, default_id: str, default_name: str,
        all_field_ids: set[str] | None,
    ) -> tuple[str, str]:
        """Bestäm vilket fält ett dokument tillhör utifrån filnamnet i JSON.

        Extraherar fältnamn-slug från dokumenttiteln och URL-katalogen.
        Om sluggen matchar ett annat känt fält returneras det, annars default.
        """
        title = doc.get("title", "").lower()
        url_path = doc.get("url", "").lower()

        # Extrahera katalognamn efter skjutfalt-och-forbud/
        pdf_field_dir = ""
        parts = url_path.split("/")
        for i, part in enumerate(parts):
            if part == "skjutfalt-och-forbud" and i + 1 < len(parts):
                pdf_field_dir = parts[i + 1]
                break

        # Extrahera fältslugg från filnamnet.
        # Typiska mönster:
        #   tilltradesforbud_trelge_v11-v21_2026.pdf
        #   tilltradesforbud-tofta-v10-v20-2026.pdf
        #   skjutvarning-blekinge-ovningsfalt-v15-v16-2026.pdf
        # Ta bort prefix (tilltradesforbud/skjutvarning) och suffix (v-nummer, årtal)
        slug_from_title = self._extract_field_slug(title)

        if not all_field_ids or not slug_from_title:
            return default_id, default_name

        # Om sluggen i filnamnet matchar default → behåll default
        if default_id.startswith(slug_from_title) or slug_from_title.startswith(default_id.split("-")[0]):
            return default_id, default_name

        # Kolla om sluggen matchar ett annat känt fält-ID
        for fid in all_field_ids:
            if fid == default_id:
                continue
            if fid.startswith(slug_from_title) or slug_from_title.startswith(fid.split("-")[0]):
                self.logger.info(
                    "Dokument '%s' under '%s' tillhör '%s' — omdirigerar",
                    title, default_name, fid,
                )
                # Rekonstruera ett läsbart namn från ID:t
                readable_name = fid.replace("-", " ").title()
                # Försök matcha mot skjutfält/övningsfält
                for suffix in ("skjutfält", "övningsfält", "övnings- och skjutfält"):
                    candidate = slug_from_title.replace("-", " ").title() + " " + suffix
                    cid = self._make_id(candidate)
                    if cid == fid:
                        readable_name = candidate
                        break
                return fid, readable_name

        # Sluggen matchar inget känt fält → skapa nytt fält-ID
        new_id = slug_from_title + "-skjutfalt"
        if new_id not in all_field_ids:
            # Prova utan suffix
            for fid in all_field_ids:
                if slug_from_title in fid:
                    return fid, default_name
        # Fallback: skapa nytt fält
        new_name = slug_from_title.replace("-", " ").title() + " skjutfält"
        self.logger.info(
            "Dokument '%s' under '%s' → nytt fält '%s'",
            title, default_name, new_name,
        )
        return self._make_id(new_name), new_name

    @staticmethod
    def _extract_field_slug(title: str) -> str:
        """Extraherar fältnamn-slug från ett PDF-filnamn.

        Exempel:
            tilltradesforbud_trelge_v11-v21_2026.pdf → trelge
            skjutvarning-blekinge-ovningsfalt-v15-v16-2026.pdf → blekinge-ovningsfalt
            tilltradesforbud-r74-arvidsjaur-v14-2026.pdf → arvidsjaur
        """
        # Ta bort filändelse
        name = re.sub(r"\.pdf$", "", title, flags=re.IGNORECASE)
        # Normalisera separatorer till bindestreck
        name = name.replace("_", "-")
        # Ta bort prefix
        name = re.sub(
            r"^(?:tilltradesforbud|skjutvarning|avlysning|varningsmeddelande)[-_]",
            "", name,
        )
        # Ta bort Försvarsmaktens beslutsnummer (t.ex. "r74-")
        name = re.sub(r"^r\d+[-_]", "", name)
        # Ta bort veckoangivelser och årtal i slutet (v10-v20-2026, v15-2026)
        name = re.sub(r"[-_]v\d+.*$", "", name)
        # Ta bort bara årtal i slutet
        name = re.sub(r"[-_]20\d{2}$", "", name)
        return name.strip("-")

    def _build_field_entry(self, field_id: str, name: str, docs: list[dict]) -> dict | None:
        """Laddar ner och parsar PDF:er för ett fält, returnerar fält-entry."""
        restrictions: list[dict] = []
        pdf_urls: list[str] = []
        for doc in docs:
            pdf_url = FM_BASE_URL + doc["url"]
            pdf_urls.append(pdf_url)
            try:
                pdf_restrictions = self._parse_pdf(pdf_url)
                # Lägg till source_url på varje restriktion
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
            "name": name,
            "source": "forsvarsmakten.se",
            "source_url": pdf_urls[0] if pdf_urls else
                FM_BASE_URL + "/regler-och-tillstand/skjutfalt-och-forbud/",
            "restrictions": unique,
        }

    def _parse_pdf(self, pdf_url: str) -> list[dict]:
        """Laddar ner och parsar en avlysnings-PDF via formatspecifik parser."""
        pdf_bytes = self.fetch_bytes(pdf_url)
        filename = pdf_url.split("/")[-1]

        try:
            full_text = self._extract_pdf_text(pdf_bytes, filename)
        except Exception as e:
            self.logger.warning("Kunde inte läsa PDF %s: %s", filename, e)
            return []

        if not full_text.strip():
            self.logger.warning("Tom PDF: %s", pdf_url)
            return []

        restrictions = parse_pdf_text(full_text, filename)
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
