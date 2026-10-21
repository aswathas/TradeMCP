"""Tiny TTL disk cache - keeps repeated screener/quote calls off the free endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from . import config


class TTLCache:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or config.CACHE_DIR
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        return self._root / f"{digest}.json"

    async def get(self, key: str, ttl: int) -> Any | None:
        path = self._path(key)
        try:
            raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
        except OSError:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if time.time() - float(payload.get("ts", 0)) > ttl:
            return None
        return payload.get("data")

    async def set(self, key: str, data: Any) -> None:
        path = self._path(key)
        payload = json.dumps({"ts": time.time(), "data": data}, default=str)
        try:
            await asyncio.to_thread(path.write_text, payload, encoding="utf-8")
        except OSError:
            pass  # cache is an optimisation, never a hard requirement


cache = TTLCache()
