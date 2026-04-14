"""Scraper för skjutfalten.se (Bofors / Villingsbergs skjutfält)."""

import re
from datetime import date, timedelta

from bs4 import BeautifulSoup

from .base import BaseScraper

BASE_URL = "https://skjutfalten.se/avlysningar"

# Mappning av bildfilnamn → sektorstatus
COLOR_MAP = {
    "red": "tilltradesforbud",
    "green": "tillgrade",
    "yellow": "ej_angivet",
}

# Regex för att extrahera sektor och färg från bildfilnamn
# Exempel: map_area_a_red.png, map_area_1_green.png
SECTOR_IMAGE_PATTERN = re.compile(r"map_area_(\w+)_(red|green|yellow)", re.IGNORECASE)


class BoforsScraper(BaseScraper):
    """Scrapar sektorstatus från skjutfalten.se."""

    def scrape(self) -> list[dict]:
        """Hämtar avlysningar för idag och kommande 7 dagar."""
        today = date.today()
        all_restrictions: list[dict] = []

        for day_offset in range(7):
            target_date = today + timedelta(days=day_offset)
            try:
                day_restrictions = self._scrape_date(target_date)
                all_restrictions.extend(day_restrictions)
            except Exception:
                self.logger.exception(
                    "Kunde inte scrapa skjutfalten.se för datum %s",
                    target_date.isoformat(),
                )

        # Bofors och Villingsberg delar samma sida
        fields = []
        if all_restrictions:
            fields.append({
                "id": "bofors-skjutfalt",
                "name": "Bofors skjutfält",
                "source": "skjutfalten.se",
                "source_url": BASE_URL,
                "restrictions": all_restrictions,
            })

        return fields

    def _scrape_date(self, target_date: date) -> list[dict]:
        """Scrapar sektorstatus för ett specifikt datum."""
        url = f"{BASE_URL}/{target_date.strftime('%d/%m/%Y')}"
        resp = self.fetch(url)
        soup = BeautifulSoup(resp.text, "lxml")

        restrictions: list[dict] = []
        date_str = target_date.isoformat()

        # Metod 1: Extrahera från bildfilnamn (map_area_X_color.png)
        for img in soup.find_all("img"):
            src = img.get("src", "")
            match = SECTOR_IMAGE_PATTERN.search(src)
            if match:
                sector = match.group(1).upper()
                color = match.group(2).lower()
                status = COLOR_MAP.get(color, "okand")

                if status == "tilltradesforbud":
                    restrictions.append({
                        "date": date_str,
                        "type": "tilltradesforbud",
                        "sectors": [sector],
                    })

        # Metod 2: Försök extrahera tider och sektorer från text
        text_content = soup.get_text()
        # Blindröjning har ofta fasta tider
        if "blindröjning" in text_content.lower() or "blind" in text_content.lower():
            # Blindröjning vanligtvis 07:00-16:00
            self.logger.info("Blindröjningsinformation hittad för %s", date_str)

        self.logger.info(
            "skjutfalten.se %s: %d aktiva tillträdesförbud",
            date_str,
            len(restrictions),
        )
        return restrictions
