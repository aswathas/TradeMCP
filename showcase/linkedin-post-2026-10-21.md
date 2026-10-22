The original TradeMCP post on LinkedIn, published 21 Oct 2026
(urn:li:ugcPost:7518685959685636096). Kept so the copy is never lost: the
21 Oct post showed the first cut of the demo page - the "Copy the MCP
config" button and the original flame art - and predated both the npm
wrapper and the Malevolent Shrine rebuild.

The refreshed version lives in showcase/linkedin-post.md.

---

I built a free Model Context Protocol server for the Indian stock market — and gave it two anime domains because I couldn't help myself.

Most finance MCP servers want an API key, a subscription, or a US ticker universe. TradeMCP wants none of that.

What your agent gets:
→ 14 tools, over plain MCP stdio
→ Live NSE/BSE quotes and OHLCV history
→ 57 technical indicators, 18 candlestick patterns
→ 54 fundamental ratios — ROCE, DuPont, working-capital days, a 0–100 health score
→ A screener over NIFTY 50 / 100 / 500
→ Portfolio analytics: beta, Sharpe, Sortino, drawdown, sector concentration

The part I'm happiest with: every ratio is computed locally from raw statement lines, not scraped off a screen. The numbers are auditable, and they always agree with each other.

Three free public sources — Yahoo Finance, NSE static archives, Screener.in. Two dependencies: mcp and httpx. That's the whole stack.

The demo page has two original themes, "Infinite Void" and "Malevolent Shrine", drawn entirely in code. The cleave cutting through the candles is the biggest single-day move in the real series; the flame sits on the best up-day. The 20 seals under the chart are the last 20 sessions, one per day, green when it closed up. Real numbers, dressed up.

MIT licensed. Free to run. No key, no signup, no cost.

Live demo → https://aswathas.github.io/TradeMCP/
Code → https://github.com/aswathas/TradeMCP

If you point this at one stock tomorrow, which one?

#ModelContextProtocol #MCP #IndianStockMarket #NSE #OpenSource #AI #Quant
