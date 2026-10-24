"""Runtime configuration. Every value can be overridden by an env var."""

from __future__ import annotations

import os
from pathlib import Path

USER_AGENT = os.getenv(
    "TRADEMCP_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
)
TIMEOUT = float(os.getenv("TRADEMCP_TIMEOUT", "30"))

CACHE_DIR = Path(os.getenv("TRADEMCP_CACHE_DIR", str(Path.home() / ".cache" / "trademcp")))

# TTLs in seconds. Prices move, fundamentals do not.
PRICE_TTL = int(os.getenv("TRADEMCP_PRICE_TTL", "900"))
QUOTE_TTL = int(os.getenv("TRADEMCP_QUOTE_TTL", "300"))
FUNDAMENTALS_TTL = int(os.getenv("TRADEMCP_FUNDAMENTALS_TTL", "21600"))
UNIVERSE_TTL = int(os.getenv("TRADEMCP_UNIVERSE_TTL", "43200"))
PROFILE_TTL = int(os.getenv("TRADEMCP_PROFILE_TTL", "86400"))

# Cap on simultaneous upstream requests (public endpoints are rate limited).
MAX_CONCURRENCY = int(os.getenv("TRADEMCP_MAX_CONCURRENCY", "8"))

# Screener.in adds India-specific ratios (ROCE, ROE, promoter holding).
ENABLE_SCREENER_IN = os.getenv("TRADEMCP_ENABLE_SCREENER_IN", "1").lower() not in ("0", "false", "no")
