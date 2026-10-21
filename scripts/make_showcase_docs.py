"""Generate the TradeMCP showcase spec sheet and live demo from the real server.

Reads the registered tools, counts the metrics the analytics engine can
produce, runs a representative set of calls against the live free data
sources, and writes two Markdown files:

    showcase/SPEC.md   the full description + tool reference
    showcase/DEMO.md   real captured output from every tool

    python scripts/make_showcase_docs.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "showcase"
OUT.mkdir(exist_ok=True)

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logging.getLogger("httpx").setLevel(logging.WARNING)

from trademcp import tools  # noqa: E402
from trademcp.analytics import fundamentals as fa  # noqa: E402
from trademcp.app import mcp  # noqa: E402
from trademcp.tools.technical import REGISTRY  # noqa: E402

DEMO_CALLS: list[tuple[str, dict, str]] = [
    ("trademcp_search_symbol", {"query": "tata motors", "limit": 4}, "Find a company by name, not ticker"),
    ("trademcp_get_quote", {"symbol": "RELIANCE"}, "Live quote plus valuation and returns"),
    ("trademcp_get_price_history", {"symbol": "INFY", "range": "1mo", "limit": 6}, "Raw OHLCV candles"),
    ("trademcp_get_index_snapshot", {"indices": ["NIFTY 50", "SENSEX", "NIFTY BANK", "INDIA VIX"]}, "Where the market stands"),
    ("trademcp_get_market_breadth", {"index": "NIFTY 50", "include_trend": False}, "Breadth across index constituents"),
    ("trademcp_compare_stocks", {"symbols": ["RELIANCE", "TCS"]}, "Side-by-side on price, quality and momentum"),
    ("trademcp_get_technical_indicators", {"symbol": "RELIANCE", "indicators": ["rsi_14", "macd", "atr_14", "supertrend"], "limit": 3}, "Any of the 57 indicators"),
    ("trademcp_get_technical_analysis", {"symbol": "HDFCBANK", "range": "1y"}, "Scored signals plus risk statistics"),
    ("trademcp_get_support_resistance", {"symbol": "SBIN"}, "Five pivot styles, fib levels, swing points"),
    ("trademcp_get_fundamentals", {"symbol": "TCS"}, "The full fundamental picture"),
    ("trademcp_get_valuation", {"symbol": "INFY"}, "Valuation sheet with a plain-English read"),
    ("trademcp_get_financial_statements", {"symbol": "RELIANCE", "years": 3}, "Income statement, balance sheet, cash flow"),
    ("trademcp_screen_stocks", {"universe": "NIFTY 50", "min_roe": 15, "max_debt_to_equity": 1.0, "limit": 5}, "Fundamental + technical screen"),
    ("trademcp_analyze_portfolio", {"holdings": [{"symbol": "RELIANCE", "quantity": 10, "cost_price": 1150}, {"symbol": "TCS", "quantity": 5, "cost_price": 2600}]}, "Portfolio risk and concentration"),
]


def count_ratios() -> dict[str, int]:
    """How many distinct ratios the fundamentals engine emits per group."""
    empty = fa.build_fundamentals({})
    groups = ["valuation", "profitability", "leverage", "liquidity", "growth", "dupont"]
    counts = {group: len(empty[group]) for group in groups}
    counts["total"] = sum(counts.values())
    return counts


async def gather() -> dict:
    listing = await mcp.list_tools()
    tools_meta = []
    for tool in listing:
        schema = tool.input_schema or {}
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        tools_meta.append(
            {
                "name": tool.name,
                "title": tool.annotations.title if tool.annotations else None,
                "description": (tool.description or "").strip(),
                "params": [
                    {"name": k, "required": k in required, "type": v.get("type", "any"), "description": v.get("description", "")}
                    for k, v in props.items()
                ],
                "read_only": bool(tool.annotations and tool.annotations.read_only_hint),
            }
        )

    demos = []
    for name, args, caption in DEMO_CALLS:
        started = time.time()
        result = await mcp.call_tool(name, args)
        text = result.content[0].text if result.content else ""
        demos.append(
            {
                "name": name,
                "args": args,
                "caption": caption,
                "output": text,
                "seconds": round(time.time() - started, 2),
                "error": text.startswith("Error:"),
            }
        )
    return {"tools": tools_meta, "demos": demos}


def write_spec(data: dict) -> str:
    tools_meta = data["tools"]
    ratios = count_ratios()
    total_params = sum(len(t["params"]) for t in tools_meta)
    required_params = sum(sum(1 for p in t["params"] if p["required"]) for t in tools_meta)

    lines: list[str] = []
    add = lines.append

    add("# TradeMCP — Specification")
    add("")
    add("A free Model Context Protocol server for Indian equities (NSE/BSE). It gives an AI agent")
    add("live market data, 57 technical indicators, full fundamental ratios, financial statements,")
    add("a stock screener and portfolio analytics. No API keys, no paid tiers, no account.")
    add("")
    add("## At a glance")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Tools | {len(tools_meta)} |")
    add(f"| Tool parameters | {total_params} ({required_params} required) |")
    add(f"| Technical indicators | {len(REGISTRY)} |")
    add(f"| Fundamental ratios | {ratios['total']} across {len(ratios) - 1} groups |")
    add("| Candlestick patterns | 18 |")
    add("| Pivot point styles | 5 |")
    add("| Indian indices covered | 15 |")
    add("| Data sources | 3, all free and keyless |")
    add("| Dependencies | 2 (`mcp`, `httpx`) |")
    add("")

    add("## How it works")
    add("")
    add("```")
    add("AI agent  ──(MCP stdio)──▶  TradeMCP server")
    add("                               │")
    add("                               ├─▶ Yahoo Finance   prices · quotes · statements")
    add("                               ├─▶ NSE static CSVs symbol universe · ISIN · industry")
    add("                               └─▶ Screener.in     ROCE · ROCE · promoter holding")
    add("```")
    add("")
    add("1. **Resolve.** Any input is normalised to an NSE code and a Yahoo ticker. `RELIANCE`,")
    add("   `tata motors`, `NSE:TCS`, `RELIANCE.NS`, `INE002A01018` and `nifty` all work.")
    add("2. **Fetch.** Price history comes from Yahoo's chart endpoint. Fundamentals come from")
    add("   Yahoo's fundamentals-timeseries endpoint. Symbol identity comes from NSE's static CSV")
    add("   listings, which are not behind the bot protection that guards NSE's live JSON API.")
    add("3. **Compute.** Every ratio is derived locally from raw statement lines, so valuation,")
    add("   profitability, leverage, liquidity and growth all reconcile with each other and with")
    add("   the DuPont identity. Nothing is copied off a screen and trusted.")
    add("4. **Score.** Indicators become directional signals, signals become a composite")
    add("   Strong Buy → Strong Sell score, and the score is explained in plain language.")
    add("5. **Cache.** Responses are cached on disk with per-type TTLs, so repeated screener and")
    add("   quote calls stay off the free endpoints and stay fast.")
    add("")

    add("## Data sources (all free, all keyless)")
    add("")
    add("| Source | Provides | Why it needs no key |")
    add("|---|---|---|")
    add("| Yahoo Finance chart | OHLCV candles, 52-week range | Public JSON endpoint |")
    add("| Yahoo Finance quote | Price, market cap, multiples, dividend yield | Public, with a free cookie + crumb handshake the server does itself |")
    add("| Yahoo fundamentals-timeseries | Annual, quarterly and trailing statement lines | Public JSON endpoint |")
    add("| NSE static CSV listings | Symbol, company, ISIN, industry, index membership | Static files, no session required |")
    add("| Screener.in | ROCE, ROCE, promoter/FII/DII holding, working-capital days | Public pages, parsed defensively, treated as optional |")
    add("")

    add("## Tool reference")
    add("")
    for tool in tools_meta:
        add(f"### `{tool['name']}`")
        add("")
        summary = tool["description"].split("\n\n")[0].replace("\n", " ")
        add(summary)
        add("")
        add("| Parameter | Type | Required | Description |")
        add("|---|---|---|---|")
        for param in tool["params"]:
            desc = param["description"].replace("\n", " ").replace("|", "\\|")
            add(f"| `{param['name']}` | {param['type']} | {'yes' if param['required'] else 'no'} | {desc} |")
        add("")

    add("## The metrics")
    add("")
    add("### Technical indicators (57)")
    add("")
    add("| Family | Indicators |")
    add("|---|---|")
    add("| Trend | `sma_20` `sma_50` `sma_200` `ema_9` `ema_21` `ema_50` `ema_200` `macd` `macd_signal` `macd_histogram` `adx_14` `plus_di` `minus_di` `supertrend` `parabolic_sar` `ichimoku_tenkan` `ichimoku_kijun` `ichimoku_senkou_a` `ichimoku_senkou_b` `aroon_up` `aroon_down` `vortex_plus` `vortex_minus` `linear_slope_20` |")
    add("| Momentum | `rsi_7` `rsi_14` `stochastic_k` `stochastic_d` `stoch_rsi_k` `cci_20` `williams_r` `mfi_14` `roc_10` `cmo_14` `tsi` `ultimate_oscillator` `awesome_oscillator` |")
    add("| Volatility | `atr_14` `true_range` `bollinger_upper` `bollinger_middle` `bollinger_lower` `bollinger_percent_b` `bollinger_bandwidth` `keltner_upper` `keltner_lower` `donchian_upper` `donchian_lower` `historical_volatility` `zscore_20` |")
    add("| Volume | `obv` `vwap` `chaikin_money_flow` `accumulation_distribution` `price_volume_trend` `force_index` `volume_ratio_20` |")
    add("")

    add("### Fundamental ratios")
    add("")
    add("| Group | Count | Ratios |")
    add("|---|---|---|")
    add(f"| Valuation | {ratios['valuation']} | P/E, PEG, P/B, P/S, EV/EBITDA, EV/Sales, market cap, enterprise value, dividend yield, EPS, book value/share, DPS |")
    add(f"| Profitability | {ratios['profitability']} | Gross / operating / EBITDA / net margin, ROE, ROA, ROCE, ROIC, asset turnover, equity multiplier, effective tax rate |")
    add(f"| Leverage | {ratios['leverage']} | Debt/equity, debt/assets, cash, net debt, net debt/EBITDA, interest coverage, debt/capital |")
    add(f"| Liquidity | {ratios['liquidity']} | Current ratio, quick ratio, cash ratio, working capital, working capital/share, operating cash flow, free cash flow, FCF margin, CFO/net income, capex, CFPS, FCFPS |")
    add(f"| Growth | {ratios['growth']} | Revenue / net income / EPS / CFO YoY, revenue and net income 3-year and 5-year CAGR |")
    add(f"| DuPont | {ratios['dupont']} | Net margin × asset turnover × equity multiplier, reconciled ROE |")
    add(f"| **Total** | **{ratios['total']}** | plus a 0-100 health score with a per-metric breakdown |")
    add("")

    add("### India-specific (Screener.in)")
    add("")
    add("ROCE, ROCE, book value, face value, market cap in crore, debt/equity, ROCE history,")
    add("debtor days, inventory days, days payable, cash conversion cycle, and the promoter /")
    add("FII / DII / government / public holding pattern with quarterly history.")
    add("")

    add("## Indices covered")
    add("")
    add("NIFTY 50, SENSEX, NIFTY BANK, NIFTY IT, NIFTY AUTO, NIFTY FMCG, NIFTY PHARMA,")
    add("NIFTY REALTY, NIFTY METAL, NIFTY MEDIA, NIFTY ENERGY, NIFTY PSU BANK,")
    add("NIFTY FINANCIAL SERVICES, NIFTY PRIVATE BANK, NIFTY 500, INDIA VIX.")
    add("")

    add("## Configuration")
    add("")
    add("| Variable | Default |")
    add("|---|---|")
    add("| `TRADEMCP_TIMEOUT` | `30` |")
    add("| `TRADEMCP_CACHE_DIR` | `~/.cache/trademcp` |")
    add("| `TRADEMCP_QUOTE_TTL` | `300` |")
    add("| `TRADEMCP_PRICE_TTL` | `900` |")
    add("| `TRADEMCP_FUNDAMENTALS_TTL` | `21600` |")
    add("| `TRADEMCP_UNIVERSE_TTL` | `43200` |")
    add("| `TRADEMCP_PROFILE_TTL` | `86400` |")
    add("| `TRADEMCP_MAX_CONCURRENCY` | `8` |")
    add("| `TRADEMCP_ENABLE_SCREENER_IN` | `1` |")
    add("")

    text = "\n".join(lines) + "\n"
    (OUT / "SPEC.md").write_text(text, encoding="utf-8")
    return text


def write_demo(data: dict) -> str:
    lines: list[str] = []
    add = lines.append

    add("# TradeMCP — Live demo")
    add("")
    add("Real output captured from the running server against live free data sources.")
    add(f"Captured {time.strftime('%Y-%m-%d %H:%M')} IST.")
    add("")
    failures = sum(1 for d in data["demos"] if d["error"])
    add(f"**{len(data['demos']) - failures}/{len(data['demos'])} tool calls returned usable output.**")
    add("")

    for demo in data["demos"]:
        add(f"## `{demo['name']}`")
        add("")
        add(f"*{demo['caption']}*")
        add("")
        add("```json")
        add(json.dumps(demo["args"], indent=2))
        add("```")
        add("")
        add(f"Took {demo['seconds']}s.")
        add("")
        add("```markdown")
        add(demo["output"].rstrip())
        add("```")
        add("")

    text = "\n".join(lines) + "\n"
    (OUT / "DEMO.md").write_text(text, encoding="utf-8")
    return text


async def main() -> int:
    data = await gather()
    spec = write_spec(data)
    demo = write_demo(data)
    print(f"wrote {OUT / 'SPEC.md'} ({len(spec)} chars)")
    print(f"wrote {OUT / 'DEMO.md'} ({len(demo)} chars)")
    failures = [d["name"] for d in data["demos"] if d["error"]]
    if failures:
        print("ERROR on:", ", ".join(failures))
        return 1
    print(f"all {len(data['demos'])} demo calls succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
