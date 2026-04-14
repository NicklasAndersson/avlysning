"""Basklass för alla scrapers."""

import logging
import time
from abc import ABC, abstractmethod

import requests


class BaseScraper(ABC):
    """Gemensam basklass med HTTP-klient, rate limiting och felhantering."""

    def __init__(self, user_agent: str, delay: float = 2.0) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._last_request_time: float = 0.0

    def fetch(self, url: str) -> requests.Response:
        """Hämtar en URL med rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            wait = self.delay - elapsed
            self.logger.debug("Rate limit: väntar %.1f s", wait)
            time.sleep(wait)

        self.logger.info("Hämtar: %s", url)
        response = self.session.get(url, timeout=30)
        self._last_request_time = time.time()
        response.raise_for_status()
        return response

    def fetch_bytes(self, url: str) -> bytes:
        """Hämtar binärdata (t.ex. PDF) med rate limiting."""
        resp = self.fetch(url)
        return resp.content

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Scrapar och returnerar en lista med fält-dicts."""
        ...
