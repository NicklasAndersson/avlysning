"""Scraper för kommunala informationssidor om skjutfält."""

from bs4 import BeautifulSoup

from .base import BaseScraper

# Kända kommunsidor med skjutfältsinfo
KOMMUN_SOURCES = [
    {
        "id": "falun-skjutfalt",
        "name": "Falun skjutfält",
        "url": "https://www.falun.se/stod--omsorg/trygg-och-saker/skjutvarningar-pa-militaromradet.html",
        "kommun": "Falun",
    },
    {
        "id": "harads-skjutfalt",
        "name": "Härads skjutfält",
        "url": "https://www.strangnas.se/bygga-bo-och-miljo/naturomraden-och-parker/harads-skjutfalt",
        "kommun": "Strängnäs",
    },
    {
        "id": "remmene-skjutfalt",
        "name": "Remmene skjutfält",
        "url": "https://www.vargarda.se/bo-bygga-och-miljo/remmene-skjutfalt.html",
        "kommun": "Vårgårda",
    },
]


class KommunScraper(BaseScraper):
    """Scrapar avlysningar från kommunala webbplatser."""

    def scrape(self) -> list[dict]:
        """Hämtar avlysningar från alla kända kommunsidor."""
        fields: list[dict] = []

        for source in KOMMUN_SOURCES:
            try:
                field_data = self._scrape_kommun(source)
                if field_data:
                    fields.append(field_data)
            except Exception:
                self.logger.exception(
                    "Kunde inte scrapa %s (%s)", source["name"], source["url"]
                )

        return fields

    def _scrape_kommun(self, source: dict) -> dict | None:
        """Scrapar en enskild kommuns sida för avlysningsdata."""
        resp = self.fetch(source["url"])
        soup = BeautifulSoup(resp.text, "lxml")

        restrictions: list[dict] = []

        # Försök hitta tabeller med avlysningsdata
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # Hoppa över header
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    restriction = self._parse_table_row(cells)
                    if restriction:
                        restrictions.append(restriction)

        # Om inga tabeller, försök hitta strukturerade listor
        if not restrictions:
            restrictions = self._parse_text_content(soup)

        self.logger.info(
            "%s: %d restriktioner hittade", source["name"], len(restrictions)
        )

        return {
            "id": source["id"],
            "name": source["name"],
            "source": f"{source['kommun']}.se",
            "source_url": source["url"],
            "restrictions": restrictions,
        }

    def _parse_table_row(self, cells: list) -> dict | None:
        """Försöker parsa en tabellrad till en restriktion."""
        import re

        texts = [cell.get_text(strip=True) for cell in cells]

        # Sök efter datumformatering (YYYY-MM-DD eller DD/MM, etc.)
        date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
        time_pattern = re.compile(r"(\d{2}[:.]\d{2})\s*[-–]\s*(\d{2}[:.]\d{2})")

        date_str = None
        start_time = None
        end_time = None

        for text in texts:
            date_match = date_pattern.search(text)
            if date_match:
                date_str = date_match.group(1)

            time_match = time_pattern.search(text)
            if time_match:
                start_time = time_match.group(1).replace(".", ":")
                end_time = time_match.group(2).replace(".", ":")

        if date_str:
            restriction: dict = {
                "date": date_str,
                "type": "skjutvarning",
                "sectors": ["all"],
            }
            if start_time and end_time:
                restriction["start"] = start_time
                restriction["end"] = end_time
            return restriction

        return None

    def _parse_text_content(self, soup: BeautifulSoup) -> list[dict]:
        """Fallback: extrahera avlysningar från löpande text."""
        import re

        text = soup.get_text()
        restrictions: list[dict] = []

        date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
        time_pattern = re.compile(r"(\d{2}[:.]\d{2})\s*[-–]\s*(\d{2}[:.]\d{2})")

        dates = date_pattern.findall(text)
        time_ranges = time_pattern.findall(text)

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

        return restrictions
