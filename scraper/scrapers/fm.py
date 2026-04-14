"""Scraper för Försvarsmaktens skjutfält och avlysningar."""

import io
import re
from urllib.parse import urljoin

import pdfplumber
from bs4 import BeautifulSoup

from .base import BaseScraper

# Samlingssida med alla skjutfält (paginerad)
FM_BASE_URL = "https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/"

# Separata undersidor
FM_SUBSITES = [
    "https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/alvdalens-skjutfalt/",
    "https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/tame-skjutfalt/",
    "https://www.forsvarsmakten.se/sv/organisation/stockholms-amfibieregemente-amf-1/stockholms-amfibieregementes-skjutfalt-och-tilltradesforbud/",
]

# Regex för att hitta datum och tider i PDF-text
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")
TIME_RANGE_PATTERN = re.compile(r"(\d{2}[:.]\d{2})\s*[-–]\s*(\d{2}[:.]\d{2})")


class FMScraper(BaseScraper):
    """Scrapar avlysnings-PDF:er från forsvarsmakten.se."""

    def scrape(self) -> list[dict]:
        """Hämtar alla skjutfält från FM:s samlingssida + undersidor."""
        fields: list[dict] = []

        # Steg 1: Hämta alla fält-URL:er från samlingssidan (paginerad)
        field_urls = self._get_field_urls()
        self.logger.info("Hittade %d fält-URL:er på samlingssidan", len(field_urls))

        # Steg 2: Lägg till kända undersidor
        for url in FM_SUBSITES:
            if url not in field_urls:
                field_urls.append(url)

        # Steg 3: Scrapa varje fält
        for url in field_urls:
            try:
                field_data = self._scrape_field_page(url)
                if field_data:
                    fields.append(field_data)
            except Exception:
                self.logger.exception("Kunde inte scrapa fältssida: %s", url)

        return fields

    def _get_field_urls(self) -> list[str]:
        """Hämtar alla URL:er till individuella fältsidor från den paginerade listan."""
        urls: list[str] = []
        page = 1

        while True:
            page_url = FM_BASE_URL if page == 1 else f"{FM_BASE_URL}?page={page}"
            try:
                resp = self.fetch(page_url)
            except Exception:
                self.logger.exception("Kunde inte hämta sida %d", page)
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Hitta alla länkar till individuella fältsidor
            field_links = soup.select("a[href*='skjutfalt-och-forbud/']")
            new_urls = []
            for link in field_links:
                href = link.get("href", "")
                if href and href != FM_BASE_URL and not href.endswith("skjutfalt-och-forbud/"):
                    full_url = urljoin(FM_BASE_URL, href)
                    if full_url not in urls:
                        new_urls.append(full_url)

            if not new_urls:
                break

            urls.extend(new_urls)

            # Kolla om det finns fler sidor
            next_link = soup.select_one("a[rel='next'], a.next, .pagination a:last-child")
            if not next_link:
                break

            page += 1
            if page > 10:  # Säkerhetsgräns
                self.logger.warning("Avbryter paginering vid sida %d", page)
                break

        return urls

    def _scrape_field_page(self, url: str) -> dict | None:
        """Scrapar en individuell fältsida: hitta PDF-länkar, ladda ner och parsa."""
        resp = self.fetch(url)
        soup = BeautifulSoup(resp.text, "lxml")

        # Hämta fältnamn från sidans rubrik
        title_tag = soup.select_one("h1")
        field_name = title_tag.get_text(strip=True) if title_tag else "Okänt fält"

        # Skapa ID från URL
        field_id = url.rstrip("/").split("/")[-1]

        # Hitta PDF-länkar
        pdf_links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.lower().endswith(".pdf"):
                pdf_url = urljoin(url, href)
                link_text = a_tag.get_text(strip=True).lower()
                if any(kw in link_text or kw in href.lower() for kw in ["skjutvarning", "tilltradesforbud", "avlysning"]):
                    pdf_links.append(pdf_url)

        # Om inga filtrerade PDF:er, ta alla PDF:er
        if not pdf_links:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if href.lower().endswith(".pdf"):
                    pdf_links.append(urljoin(url, href))

        self.logger.info("Fält '%s': %d PDF:er hittade", field_name, len(pdf_links))

        # Parsa PDF:er
        restrictions: list[dict] = []
        for pdf_url in pdf_links:
            try:
                pdf_restrictions = self._parse_pdf(pdf_url)
                restrictions.extend(pdf_restrictions)
            except Exception:
                self.logger.exception("Kunde inte parsa PDF: %s", pdf_url)

        return {
            "id": field_id,
            "name": field_name,
            "source": "forsvarsmakten.se",
            "source_url": url,
            "restrictions": restrictions,
        }

    def _parse_pdf(self, pdf_url: str) -> list[dict]:
        """Laddar ner och parsar en avlysnings-PDF."""
        pdf_bytes = self.fetch_bytes(pdf_url)
        restrictions: list[dict] = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        if not full_text.strip():
            self.logger.warning("Tom PDF: %s", pdf_url)
            return []

        # Enkel parsning: hitta datum och tidsintervall
        dates = DATE_PATTERN.findall(full_text)
        time_ranges = TIME_RANGE_PATTERN.findall(full_text)

        # Koppla ihop datum med tider (förenklad logik — behöver fältspecifik parsning)
        for date_str in dates:
            restriction: dict = {
                "date": date_str,
                "type": "skjutvarning",
                "sectors": ["all"],
            }
            if time_ranges:
                start, end = time_ranges[0]
                restriction["start"] = start.replace(".", ":")
                restriction["end"] = end.replace(".", ":")
            restrictions.append(restriction)

        self.logger.info("PDF %s: %d datum, %d tidsangivelser", pdf_url, len(dates), len(time_ranges))
        return restrictions
