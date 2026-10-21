"""Serve the TradeMCP showcase with a live API backed by the MCP server.

The static page calls /api/* for live data. Those endpoints call the server's
own tools, so the page's live numbers are the product's real output rather than
a re-implementation. Opening showcase/site as a plain static folder still
works: the page falls back to the bundled snapshot.

    python scripts/serve_showcase.py [--port 8099]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import mimetypes
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logging.getLogger("httpx").setLevel(logging.WARNING)

from trademcp import tools  # noqa: F401,E402
from trademcp.app import mcp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "showcase" / "site"

TAPE_SYMBOLS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK",
    "SBIN", "ITC", "BPCL", "COALINDIA",
]

_loop: asyncio.AbstractEventLoop | None = None


def run_async(coro):
    assert _loop is not None
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()


async def call_tool(name: str, args: dict[str, Any]) -> Any:
    result = await mcp.call_tool(name, args)
    text = result.content[0].text if result.content else ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


async def api_quote(symbol: str) -> Any:
    return await call_tool("trademcp_get_quote", {"symbol": symbol, "response_format": "json"})


async def api_history(symbol: str, range_: str) -> Any:
    return await call_tool(
        "trademcp_get_price_history",
        {"symbol": symbol, "range": range_, "interval": "1d", "response_format": "json"},
    )


async def api_fundamentals(symbol: str) -> Any:
    return await call_tool(
        "trademcp_get_fundamentals", {"symbol": symbol, "response_format": "json"}
    )


async def api_indicators(symbol: str) -> Any:
    return await call_tool(
        "trademcp_get_technical_indicators",
        {"symbol": symbol, "range": "6mo", "interval": "1d", "limit": 1, "response_format": "json"},
    )


async def api_score(symbol: str) -> Any:
    """The composite technical score behind the hero gauge.

    Uses the same tool and the same 1y window the screener uses, so the gauge
    and the screener row for the same symbol always agree.
    """
    analysis = await call_tool(
        "trademcp_get_technical_analysis",
        {
            "symbol": symbol,
            "range": "1y",
            "benchmark": "NONE",
            "response_format": "json",
        },
    )
    summary = analysis.get("summary") if isinstance(analysis, dict) else None
    if not isinstance(summary, dict):
        return {"score": None, "label": None}
    return {
        "score": summary.get("score"),
        "label": summary.get("label"),
        "bullish": summary.get("bullish"),
        "bearish": summary.get("bearish"),
        "neutral": summary.get("neutral"),
        "total_signals": summary.get("total_signals"),
    }


async def api_tape() -> Any:
    rows = await asyncio.gather(
        *(api_quote(symbol) for symbol in TAPE_SYMBOLS), return_exceptions=True
    )
    out = []
    for symbol, row in zip(TAPE_SYMBOLS, rows):
        if isinstance(row, Exception):
            continue
        out.append(
            {
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "price": row.get("price"),
                "change_pct": row.get("change_pct"),
                "last_traded_at": row.get("last_traded_at"),
            }
        )
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter console
        pass

    def end_headers(self) -> None:
        # Dev server: never let the browser cache a stylesheet we just edited.
        # Without this, Chromium heuristically caches the static files and the
        # page keeps rendering the previous version of the CSS and JS.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            query = parse_qs(parsed.query)
            route = parsed.path[len("/api/"):]
            symbol = (query.get("symbol") or ["RELIANCE"])[0].upper()
            try:
                if route == "quote":
                    payload = run_async(api_quote(symbol))
                elif route == "history":
                    payload = run_async(api_history(symbol, (query.get("range") or ["6mo"])[0]))
                elif route == "fundamentals":
                    payload = run_async(api_fundamentals(symbol))
                elif route == "indicators":
                    payload = run_async(api_indicators(symbol))
                elif route == "tape":
                    payload = run_async(api_tape())
                elif route == "score":
                    payload = run_async(api_score(symbol))
                else:
                    self._send_json({"error": f"unknown endpoint {route}"}, 404)
                    return
            except Exception as exc:  # noqa: BLE001
                self._send_json({"error": f"{type(exc).__name__}: {exc}"}, 502)
                return
            self._send_json(payload)
            return

        if parsed.path in ("", "/"):
            self.path = "/index.html"
        super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    global _loop
    _loop = asyncio.new_event_loop()

    def run_loop() -> None:
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    thread = threading.Thread(target=run_loop, name="trademcp-loop", daemon=True)
    thread.start()
    time.sleep(0.2)

    mimetypes.add_type("image/webp", ".webp")
    mimetypes.add_type("application/json", ".json")

    handler = partial(Handler)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"TradeMCP showcase on http://{args.host}:{args.port}/")
    print(
        "live API: /api/quote /api/history /api/fundamentals "
        "/api/indicators /api/tape /api/score"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
