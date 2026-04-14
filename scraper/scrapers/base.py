"""Basklass för alla scrapers."""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests

# Standard-cache i projektets tmp-mapp
_DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent / "tmp" / "cache"


class BaseScraper(ABC):
    """Gemensam basklass med HTTP-klient, rate limiting och felhantering."""

    MAX_RETRIES = 3
    RETRY_BACKOFF = 3.0  # Sekunder, multipliceras med försöksnummer

    def __init__(
        self,
        user_agent: str,
        delay: float = 3.0,
        cache_ttl: int = 86400,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._last_request_time: float = 0.0
        self._cache_ttl = cache_ttl
        self._cache_dir = _DEFAULT_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _rate_limit(self) -> None:
        """Väntar tillräckligt länge sedan senaste anrop."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            wait = self.delay - elapsed
            self.logger.debug("Rate limit: väntar %.1f s", wait)
            time.sleep(wait)

    @staticmethod
    def _cache_key(url: str) -> str:
        """Skapar en filsystemsäker nyckel från en URL."""
        return hashlib.sha256(url.encode()).hexdigest()

    def _read_cache(self, url: str, binary: bool = False) -> bytes | str | None:
        """Läser cachad data om den finns och inte har gått ut."""
        key = self._cache_key(url)
        meta_path = self._cache_dir / f"{key}.meta"
        data_path = self._cache_dir / f"{key}.data"

        if not meta_path.exists() or not data_path.exists():
            return None

        try:
            meta = json.loads(meta_path.read_text())
            age = time.time() - meta["ts"]
            if age > self._cache_ttl:
                self.logger.debug("Cache utgången (%.0f s) för %s", age, url)
                return None
        except (json.JSONDecodeError, KeyError):
            return None

        self.logger.debug("Cache-träff för %s", url)
        if binary:
            return data_path.read_bytes()
        return data_path.read_text(encoding="utf-8")

    def _write_cache(self, url: str, data: bytes | str) -> None:
        """Skriver data till disk-cachen."""
        key = self._cache_key(url)
        meta_path = self._cache_dir / f"{key}.meta"
        data_path = self._cache_dir / f"{key}.data"

        meta = {"url": url, "ts": time.time()}
        meta_path.write_text(json.dumps(meta))

        if isinstance(data, bytes):
            data_path.write_bytes(data)
        else:
            data_path.write_text(data, encoding="utf-8")

    def fetch(self, url: str) -> requests.Response:
        """Hämtar en URL med cache, rate limiting och retry vid anslutningsfel."""
        cached = self._read_cache(url)
        if cached is not None:
            self.logger.info("Cache: %s", url)
            resp = requests.Response()
            resp.status_code = 200
            resp._content = cached.encode("utf-8") if isinstance(cached, str) else cached
            resp.encoding = "utf-8"
            return resp

        last_error: Exception | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            self._rate_limit()
            self.logger.info("Hämtar: %s (försök %d/%d)", url, attempt, self.MAX_RETRIES)

            try:
                response = self.session.get(url, timeout=30)
                self._last_request_time = time.time()
                response.raise_for_status()
                self._write_cache(url, response.text)
                return response
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                self.logger.warning(
                    "Anslutningsfel vid %s (försök %d/%d): %s",
                    url, attempt, self.MAX_RETRIES, exc,
                )
                # Stäng gamla anslutningar och vänta med backoff
                self.session.close()
                backoff = self.RETRY_BACKOFF * attempt
                self.logger.info("Väntar %.0f s innan nästa försök...", backoff)
                time.sleep(backoff)
                self._last_request_time = time.time()

        raise last_error  # type: ignore[misc]

    def fetch_bytes(self, url: str) -> bytes:
        """Hämtar binärdata (t.ex. PDF) med cache och rate limiting."""
        cached = self._read_cache(url, binary=True)
        if cached is not None:
            self.logger.info("Cache: %s", url)
            return cached  # type: ignore[return-value]

        last_error: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            self._rate_limit()
            self.logger.info("Hämtar: %s (försök %d/%d)", url, attempt, self.MAX_RETRIES)
            try:
                response = self.session.get(url, timeout=30)
                self._last_request_time = time.time()
                response.raise_for_status()
                self._write_cache(url, response.content)
                return response.content
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                self.logger.warning(
                    "Anslutningsfel vid %s (försök %d/%d): %s",
                    url, attempt, self.MAX_RETRIES, exc,
                )
                self.session.close()
                backoff = self.RETRY_BACKOFF * attempt
                self.logger.info("Väntar %.0f s innan nästa försök...", backoff)
                time.sleep(backoff)
                self._last_request_time = time.time()
        raise last_error  # type: ignore[misc]

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Scrapar och returnerar en lista med fält-dicts."""
        ...
