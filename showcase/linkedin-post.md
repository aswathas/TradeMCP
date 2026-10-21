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

Now it installs in one line:
npx -y @aswathas/trademcp
or, for Claude:
claude mcp add trademcp -- npx -y @aswathas/trademcp

The demo page has two original themes, "Infinite Void" and "Malevolent Shrine". The Shrine is built from my own art — a temple roof with skulls crowning the live panel, a demon maw around the price, a neon gate frame around the hero. The cleave cutting through the candles is the biggest single-day move in the real series; the flame sits on the best up-day. The 20 seals under the chart are the last 20 sessions, one per day, green when it closed up. Real numbers, dressed up.

The demo refreshes itself now: it calls the same tools your agent calls, so what the page shows is what the agent gets.

MIT licensed. Free to run. No key, no signup, no cost.

Live demo → https://aswathas.github.io/TradeMCP/
Code → https://github.com/aswathas/TradeMCP

If you point this at one stock tomorrow, which one?

#ModelContextProtocol #MCP #IndianStockMarket #NSE #OpenSource #AI #Quant
