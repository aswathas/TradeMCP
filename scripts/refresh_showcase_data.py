"""Write the showcase's fallback data straight out of the TradeMCP server.

The static page renders this snapshot immediately, then replaces it with live
data fetched in the browser. Because the snapshot comes from the server's own
tools, the fallback is proof of the product rather than a mock.

    python scripts/refresh_showcase_data.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logging.getLogger("httpx").setLevel(logging.WARNING)

from trademcp import tools  # noqa: F401,E402
from trademcp.app import mcp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "showcase" / "site" / "data" / "snapshot.json"

TAPE_SYMBOLS = [
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "SBIN",
    "ITC",
    "BPCL",
    "COALINDIA",
]

CHART_SYMBOL = "RELIANCE"
FUNDAMENTAL_SYMBOLS = ["RELIANCE", "TCS", "INFY"]


async def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    result = await mcp.call_tool(name, args)
    text = result.content[0].text if result.content else ""
    return json.loads(text)


async def main() -> int:
    tape: list[dict[str, Any]] = []
    for symbol in TAPE_SYMBOLS:
        try:
            quote = await call("trademcp_get_quote", {"symbol": symbol, "response_format": "json"})
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {symbol}: {exc}", file=sys.stderr)
            continue
        tape.append(
            {
                "symbol": quote["symbol"],
                "name": quote.get("name"),
                "price": quote.get("price"),
                "change_pct": quote.get("change_pct"),
                "last_traded_at": quote.get("last_traded_at"),
            }
        )
        print(f"  {symbol:12} {quote.get('price')}  {quote.get('change_pct')}%")

    history = await call(
        "trademcp_get_price_history",
        {"symbol": CHART_SYMBOL, "range": "6mo", "interval": "1d", "response_format": "json"},
    )
    print(f"  chart: {len(history.get('candles', []))} candles")

    fundamentals: dict[str, Any] = {}
    for symbol in FUNDAMENTAL_SYMBOLS:
        try:
            fundamentals[symbol] = await call(
                "trademcp_get_fundamentals", {"symbol": symbol, "response_format": "json"}
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  skip fundamentals {symbol}: {exc}", file=sys.stderr)

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "TradeMCP server tools (Yahoo Finance, NSE archives, Screener.in)",
        "chart_symbol": CHART_SYMBOL,
        "tape": tape,
        "candles": history.get("candles", []),
        "fundamentals": fundamentals,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    size = OUT.stat().st_size
    print(f"wrote {OUT} ({size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
