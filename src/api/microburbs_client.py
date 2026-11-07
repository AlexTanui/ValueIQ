"""Minimal Microburbs API client with retry, rate limiting and an on-disk cache.

The key is read from MICROBURBS_API_KEY and is never logged. Cached responses
live in cache/api/ (git-ignored) because API output must not be published.
"""
import hashlib
import json
import logging
import os
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_URL = "https://api-ht.microburbs.com.au"
CACHE_DIR = Path(__file__).resolve().parents[2] / "cache" / "api"
MIN_INTERVAL = 0.11  # ~9 req/s, under the ~10 req/s limit

log = logging.getLogger("microburbs")


class MicroburbsClient:
    def __init__(self, api_key=None, timeout=30, use_cache=True):
        self.api_key = api_key or os.environ["MICROBURBS_API_KEY"]
        self.timeout = timeout
        self.use_cache = use_cache
        self._last_call = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        })
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, path, params):
        key = json.dumps([path, params or {}], sort_keys=True)
        return CACHE_DIR / f"{hashlib.sha1(key.encode()).hexdigest()}.json"

    def get_payload(self, path, params=None, max_retries=4):
        """Return the full JSON payload ({data, available, ...}) or None on 403/404."""
        cache_file = self._cache_path(path, params)
        if self.use_cache and cache_file.exists():
            return json.loads(cache_file.read_text())

        url = f"{BASE_URL}{path}"
        for attempt in range(max_retries + 1):
            wait = MIN_INTERVAL - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            start = time.monotonic()
            response = self.session.get(url, params=params, timeout=self.timeout)
            self._last_call = time.monotonic()
            log.info("GET %s -> %s (%.2fs)", path, response.status_code, self._last_call - start)

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == max_retries:
                    response.raise_for_status()
                time.sleep(min(2 ** attempt, 16))
                continue
            if response.status_code in (403, 404):
                log.warning("GET %s -> %s (outside coverage or not found)", path, response.status_code)
                return None

            response.raise_for_status()
            payload = response.json()
            if self.use_cache:
                cache_file.write_text(json.dumps(payload))
            return payload
        return None

    def get(self, path, params=None, max_retries=4):
        """Return payload['data'], or None when unavailable."""
        payload = self.get_payload(path, params, max_retries)
        if not payload or payload.get("available") is False:
            return None
        return payload.get("data")
