"""NSE India provider.

Uses the public static CSV listings under nsearchives.nseindia.com. These are
not behind the bot protection that guards NSE's live JSON API, and they need no
session, so the server stays reliable and keyless.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from .. import config
from ..cache import cache
from ..http import get_text

_BASE = "https://nsearchives.nseindia.com/content"

INDEX_LISTS: dict[str, str] = {
    "NIFTY 50": "indices/ind_nifty50list.csv",
    "NIFTY 100": "indices/ind_nifty100list.csv",
    "NIFTY 500": "indices/ind_nifty500list.csv",
    "NIFTY TOTAL MARKET": "indices/ind_niftytotalmarket_list.csv",
}

_EQUITY_MASTER = "equities/EQUITY_L.csv"


def _rows(text: str) -> list[list[str]]:
    return [r for r in csv.reader(io.StringIO(text)) if r and any(c.strip() for c in r)]


def _merge_extra(row: list[str], index: int, expected: int) -> list[str]:
    """Re-join fields that were split by an unquoted comma inside a name."""
    if len(row) <= expected:
        return row
    extra = len(row) - expected
    head = row[: index + 1]
    tail = row[index + 1 + extra :]
    merged = ", ".join(part.strip() for part in row[index : index + 1 + extra] if part.strip())
    return head + [merged] + tail


async def _fetch_csv(path: str, *, source: str) -> list[list[str]]:
    text = await get_text(f"{_BASE}/{path}", source=source)
    return _rows(text)


async def get_index_constituents(index: str) -> list[dict[str, Any]]:
    """Constituents of an NSE index with company name, industry and ISIN."""
    path = INDEX_LISTS.get(index.upper())
    if not path:
        raise KeyError(
            f"Unknown index '{index}'. Available: {', '.join(sorted(INDEX_LISTS))}"
        )

    cache_key = f"nse:index:{index.upper()}"
    cached = await cache.get(cache_key, config.UNIVERSE_TTL)
    if cached:
        return cached

    rows = await _fetch_csv(path, source=f"NSE index list ({index})")
    out: list[dict[str, Any]] = []
    for row in rows[1:]:
        row = _merge_extra(row, 0, 5)
        if len(row) < 4:
            continue
        symbol = row[2].strip().upper()
        if not symbol:
            continue
        out.append(
            {
                "symbol": symbol,
                "company": row[0].strip(),
                "industry": row[1].strip(),
                "series": row[3].strip(),
                "isin": row[4].strip() if len(row) > 4 else "",
                "index": index.upper(),
            }
        )

    await cache.set(cache_key, out)
    return out


async def get_equity_master() -> dict[str, dict[str, Any]]:
    """Every NSE-listed equity: symbol -> name, ISIN, series, market lot."""
    cache_key = "nse:equity_master"
    cached = await cache.get(cache_key, config.UNIVERSE_TTL)
    if cached:
        return cached

    rows = await _fetch_csv(_EQUITY_MASTER, source="NSE equity master list")
    out: dict[str, dict[str, Any]] = {}
    for row in rows[1:]:
        row = _merge_extra(row, 1, 8)
        if len(row) < 7:
            continue
        symbol = row[0].strip().upper()
        if not symbol:
            continue
        out[symbol] = {
            "symbol": symbol,
            "name": row[1].strip(),
            "series": row[2].strip(),
            "listed_on": row[3].strip(),
            "paid_up_value": row[4].strip(),
            "market_lot": row[5].strip(),
            "isin": row[6].strip(),
            "face_value": row[7].strip() if len(row) > 7 else "",
        }

    await cache.set(cache_key, out)
    return out


async def get_sectors() -> list[str]:
    """Distinct industry names across the NIFTY 500 - used to group sector moves."""
    constituents = await get_index_constituents("NIFTY 500")
    return sorted({c["industry"] for c in constituents if c.get("industry")})
