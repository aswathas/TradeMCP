"""Live end-to-end check of every TradeMCP tool.

Runs each tool against the real free data sources and reports pass/fail with a
short excerpt of the output.

    python scripts/verify_all_tools.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Any

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from trademcp import tools  # noqa: F401,E402
from trademcp.app import mcp  # noqa: E402

CASES: list[tuple[str, dict[str, Any]]] = [
    ("trademcp_search_symbol", {"query": "tata motors", "limit": 5}),
    ("trademcp_get_quote", {"symbol": "RELIANCE"}),
    ("trademcp_get_quote", {"symbol": "tata motors", "exchange": "BSE"}),
    ("trademcp_get_price_history", {"symbol": "INFY", "range": "3mo", "limit": 5}),
    ("trademcp_get_index_snapshot", {"indices": ["NIFTY 50", "SENSEX", "NIFTY BANK", "INDIA VIX"]}),
    ("trademcp_get_market_breadth", {"index": "NIFTY 50", "include_trend": False}),
    ("trademcp_compare_stocks", {"symbols": ["RELIANCE", "TCS", "INFY"]}),
    ("trademcp_get_technical_indicators", {"symbol": "RELIANCE", "indicators": ["rsi_14", "macd", "atr_14"], "limit": 3}),
    ("trademcp_get_technical_analysis", {"symbol": "HDFCBANK", "range": "1y"}),
    ("trademcp_get_support_resistance", {"symbol": "SBIN"}),
    ("trademcp_get_fundamentals", {"symbol": "TCS"}),
    ("trademcp_get_valuation", {"symbol": "INFY"}),
    ("trademcp_get_financial_statements", {"symbol": "RELIANCE", "years": 3}),
    ("trademcp_screen_stocks", {"universe": "NIFTY 50", "min_roe": 10, "max_debt_to_equity": 1.0, "limit": 5}),
    (
        "trademcp_analyze_portfolio",
        {"holdings": [{"symbol": "RELIANCE", "quantity": 10, "cost_price": 1150}, {"symbol": "TCS", "quantity": 5}]},
    ),
]


async def main() -> int:
    failures = 0
    print(f"{'TOOL':46} {'STATUS':8} {'TIME':>7}  NOTE")
    print("-" * 100)

    for name, args in CASES:
        started = time.time()
        try:
            result = await mcp.call_tool(name, args)
            elapsed = time.time() - started
            text = result.content[0].text if result.content else ""
            errored = result.is_error or text.startswith("Error:")
            if errored:
                failures += 1
                status = "FAIL"
                note = text[:120].replace("\n", " ")
            else:
                status = "ok"
                note = f"{len(text)} chars"
            print(f"{name:46} {status:8} {elapsed:6.1f}s  {note}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"{name:46} {'EXC':8} {time.time() - started:6.1f}s  {type(exc).__name__}: {exc}")

    print("-" * 100)
    print(f"{len(CASES) - failures}/{len(CASES)} tools returned usable output")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
