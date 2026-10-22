"""Add a real NIFTY 50 screener result to the showcase snapshot.

Runs the server's own screen_stocks tool with no filters so every constituent
comes back with its metrics. The page then re-applies the same predicates in
the browser, which is exactly what the server does server-side.

    python scripts/refresh_screener_data.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logging.getLogger("httpx").setLevel(logging.WARNING)

from trademcp import tools  # noqa: F401,E402
from trademcp.app import mcp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "showcase" / "site" / "data" / "screener.json"

FIELDS = [
    "symbol", "name", "industry", "price", "change_pct", "market_cap",
    "pe_ratio", "price_to_book", "eps", "dividend_yield_pct", "week_52_high",
    "week_52_low", "volume", "roe_pct", "roce_pct", "net_margin_pct",
    "debt_to_equity", "revenue_cagr_3y_pct", "health_score", "technical_score",
    "technical_label", "rsi_14",
]


async def main() -> int:
    result = await mcp.call_tool(
        "trademcp_screen_stocks",
        {"universe": "NIFTY 50", "limit": 50, "sort_by": "market_cap", "sort_order": "desc", "response_format": "json"},
    )
    text = result.content[0].text if result.content else ""
    payload = json.loads(text)

    raw_rows = payload if isinstance(payload, list) else payload.get("matches") or payload.get("rows") or payload.get("results") or []
    print(f"raw keys: {list(payload)[:12] if isinstance(payload, dict) else type(payload)}")
    rows = []
    for row in raw_rows:
        rows.append({field: row.get(field) for field in FIELDS})
    rows = [r for r in rows if r.get("symbol")]
    print(f"{len(rows)} screener rows")

    # RSI is computed by the server but compare_stocks does not surface it, so
    # ask the technical tool for the latest value on each name.
    async def rsi_for(symbol: str):
        try:
            result = await mcp.call_tool(
                "trademcp_get_technical_indicators",
                {"symbol": symbol, "indicators": ["rsi_14"], "range": "6mo", "interval": "1d", "limit": 1, "response_format": "json"},
            )
            data = json.loads(result.content[0].text)
            series = (data.get("series") or {}).get("rsi_14") or {}
            return symbol, series.get("latest")
        except Exception:  # noqa: BLE001
            return symbol, None

    rsi_results = await asyncio.gather(*(rsi_for(s) for s in [r["symbol"] for r in rows]))
    rsi_map = dict(rsi_results)
    for row in rows:
        row["rsi_14"] = rsi_map.get(row["symbol"])
    print(f"RSI for {sum(1 for v in rsi_map.values() if v is not None)}/{len(rsi_map)} names")

    # The screener rows carry no name, technicals or RSI. compare_stocks does,
    # so walk the universe five at a time and merge.
    symbols = [r["symbol"] for r in rows]
    merged = 0
    for start in range(0, len(symbols), 5):
        chunk = symbols[start:start + 5]
        try:
            comparison = await mcp.call_tool(
                "trademcp_compare_stocks",
                {"symbols": chunk, "response_format": "json"},
            )
            text = comparison.content[0].text if comparison.content else ""
            data = json.loads(text)
        except Exception as exc:  # noqa: BLE001
            print(f"  compare {chunk}: {exc}", file=sys.stderr)
            continue
        compared = data if isinstance(data, list) else data.get("stocks") or data.get("comparison") or data.get("matches") or data.get("rows") or []
        if isinstance(compared, dict):
            compared = compared.get("rows", [])
        for other in compared:
            target = next((r for r in rows if r["symbol"] == other.get("symbol")), None)
            if not target:
                continue
            for key in ("name", "industry", "change_pct", "eps", "week_52_high", "week_52_low",
                        "volume", "technical_score", "technical_label", "rsi_14"):
                if target.get(key) is None and other.get(key) is not None:
                    target[key] = other[key]
            merged += 1
        print(f"  compared {chunk} -> {merged} merged")

    print(f"{len(rows)} rows, {merged} enriched")

    out = {
        "universe": "NIFTY 50",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "trademcp_screen_stocks via the TradeMCP server",
        "fields": FIELDS,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
    if rows:
        print("sample:", json.dumps(rows[0], ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
