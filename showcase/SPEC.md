# TradeMCP — Specification

A free Model Context Protocol server for Indian equities (NSE/BSE). It gives an AI agent
live market data, 57 technical indicators, full fundamental ratios, financial statements,
a stock screener and portfolio analytics. No API keys, no paid tiers, no account.

## At a glance

| | |
|---|---|
| Tools | 14 |
| Tool parameters | 64 (11 required) |
| Technical indicators | 57 |
| Fundamental ratios | 54 across 6 groups |
| Candlestick patterns | 18 |
| Pivot point styles | 5 |
| Indian indices in the default snapshot | 15 |
| Data sources | 3, all free and keyless |
| Dependencies | 2 (`mcp`, `httpx`) |

## How it works

```
AI agent  ──(MCP stdio)──▶  TradeMCP server
                               │
                               ├─▶ Yahoo Finance   prices · quotes · statements
                               ├─▶ NSE static CSVs symbol universe · ISIN · industry
                               └─▶ Screener.in     ROCE · ROE · promoter holding
```

1. **Resolve.** Any input is normalised to an NSE code and a Yahoo ticker. `RELIANCE`,
   `tata motors`, `NSE:TCS`, `RELIANCE.NS`, `INE002A01018` and `nifty` all work.
2. **Fetch.** Price history comes from Yahoo's chart endpoint. Fundamentals come from
   Yahoo's fundamentals-timeseries endpoint. Symbol identity comes from NSE's static CSV
   listings, which are not behind the bot protection that guards NSE's live JSON API.
3. **Compute.** Every ratio is derived locally from raw statement lines, so valuation,
   profitability, leverage, liquidity and growth all reconcile with each other and with
   the DuPont identity. Nothing is copied off a screen and trusted.
4. **Score.** Indicators become directional signals, signals become a composite
   Strong Buy → Strong Sell score, and the score is explained in plain language.
5. **Cache.** Responses are cached on disk with per-type TTLs, so repeated screener and
   quote calls stay off the free endpoints and stay fast.

## Data sources (all free, all keyless)

| Source | Provides | Why it needs no key |
|---|---|---|
| Yahoo Finance chart | OHLCV candles, 52-week range | Public JSON endpoint |
| Yahoo Finance quote | Price, market cap, multiples, dividend yield | Public, with a free cookie + crumb handshake the server does itself |
| Yahoo fundamentals-timeseries | Annual, quarterly and trailing statement lines | Public JSON endpoint |
| NSE static CSV listings | Symbol, company, ISIN, industry, index membership | Static files, no session required |
| Screener.in | ROCE, ROE, promoter/FII/DII holding, working-capital days | Public pages, parsed defensively, treated as optional |

## Tool reference

### `trademcp_get_fundamentals`

Get a full fundamental picture of an Indian stock.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | NSE symbol or company name, e.g. 'HDFCBANK' |
| `include_india_metrics` | boolean | no | Include India-specific ratios from Screener.in (ROCE, ROE, promoter holding, working-capital days) |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_get_valuation`

Get a focused valuation sheet for an Indian stock.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | NSE symbol or company name, e.g. 'BAJFINANCE' |
| `peers` | boolean | no | Also fetch a small peer set from the same NSE industry for comparison |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_get_financial_statements`

Get income statement, balance sheet and cash flow line items for a stock.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | NSE symbol or company name, e.g. 'SBIN' |
| `period` | string | no | 'annual' or 'quarterly' |
| `years` | integer | no | How many periods to include (1-10) |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_search_symbol`

Search NSE-listed companies by ticker symbol or company name.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | yes | Symbol code or company name to search, e.g. 'RELIANCE', 'tata', 'bank of baroda' |
| `limit` | integer | no | Maximum results to return (1-50) |
| `response_format` | any | no | 'markdown' for readable output or 'json' for structured data |

### `trademcp_get_quote`

Get the latest price quote and key statistics for an Indian stock.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | NSE symbol or company name, e.g. 'RELIANCE' or 'tata motors' |
| `exchange` | string | no | Preferred listing: 'NSE' or 'BSE' |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_get_price_history`

Get historical OHLCV candles for an Indian stock.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | NSE symbol or company name, e.g. 'INFY' |
| `range` | string | no | Lookback window: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max |
| `interval` | string | no | Bar size: 1d, 1wk, 1mo, 1h, 30m, 15m, 5m |
| `limit` | integer | no | Maximum number of candles to return (1-500) |
| `exchange` | string | no | 'NSE' or 'BSE' |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_get_index_snapshot`

Get live quotes for major Indian indices.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `indices` | any | no | Index names to fetch, e.g. ['NIFTY 50','SENSEX','NIFTY BANK']. Omit for the default set. |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_get_market_breadth`

Measure market breadth for an Indian index.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `index` | string | no | Index whose constituents are analysed: 'NIFTY 50' or 'NIFTY 100' |
| `include_trend` | boolean | no | Also compute the share of constituents above their 200-day moving average (slower) |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_compare_stocks`

Compare two to five Indian stocks across price, valuation, quality and momentum.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbols` | array | yes | Two to five NSE symbols or company names to compare side by side |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_screen_stocks`

Screen Indian stocks by fundamental and technical criteria.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `universe` | string | no | Stock universe to scan: 'NIFTY 50', 'NIFTY 100', 'NIFTY 500' or 'NSE' (the NSE universe is the first 600 symbols in NSE listing order, not every listed stock) |
| `min_pe` | any | no | Only stocks with P/E at or above this (a floor) |
| `max_pe` | any | no | Only stocks with P/E at or below this (a ceiling) |
| `min_roe` | any | no | Minimum return on equity (%) |
| `min_roce` | any | no | Minimum return on capital employed (%) |
| `min_net_margin` | any | no | Minimum net profit margin (%) |
| `max_debt_to_equity` | any | no | Maximum debt to equity ratio |
| `min_market_cap` | any | no | Minimum market cap in rupees |
| `min_dividend_yield` | any | no | Minimum dividend yield (%) |
| `min_current_ratio` | any | no | Minimum current ratio |
| `min_revenue_cagr` | any | no | Minimum 3-year revenue CAGR (%) |
| `rsi_below` | any | no | Only stocks with RSI under this (oversold screen) |
| `rsi_above` | any | no | Only stocks with RSI over this (overbought screen) |
| `above_sma50` | any | no | Only stocks trading above their 50-day average |
| `above_sma200` | any | no | Only stocks trading above their 200-day average |
| `limit` | integer | no | Maximum stocks to return (1-100) |
| `sort_by` | string | no | Sort field: 'market_cap', 'pe_ratio', 'price_to_book', 'roe_pct', 'roce_pct', 'revenue_cagr_3y_pct', 'dividend_yield_pct', 'health_score' |
| `sort_order` | string | no | Sort direction: 'desc' or 'asc' |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_analyze_portfolio`

Analyse an Indian equity portfolio.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `holdings` | array | yes | Positions to analyse, e.g. [{'symbol':'RELIANCE','quantity':10,'cost_price':1200}] |
| `benchmark` | string | no | Benchmark index: 'NIFTY 50' or 'SENSEX' |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_get_technical_indicators`

Compute technical indicators for an Indian stock.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | NSE symbol or company name, e.g. 'RELIANCE' |
| `indicators` | any | no | Indicator names to compute, e.g. ['rsi_14','macd','atr_14']. Omit for all 57. |
| `range` | string | no | Lookback window: 3mo, 6mo, 1y, 2y, 5y |
| `interval` | string | no | Bar size: 1d, 1wk, 1h, 30m |
| `limit` | integer | no | How many recent data points to keep per indicator (1-100) |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_get_technical_analysis`

Run a full technical analysis and produce a directional read on a stock.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | NSE symbol or company name, e.g. 'INFY' |
| `range` | string | no | Lookback window: 6mo, 1y, 2y, 5y |
| `benchmark` | string | no | Benchmark index for beta/relative strength: 'NIFTY 50' or 'SENSEX' |
| `response_format` | any | no | 'markdown' or 'json' |

### `trademcp_get_support_resistance`

Compute support and resistance levels for an Indian stock.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbol` | string | yes | NSE symbol or company name, e.g. 'TCS' |
| `range` | string | no | Lookback window: 6mo, 1y, 2y, 5y |
| `response_format` | any | no | 'markdown' or 'json' |

## The metrics

### Technical indicators (57)

| Family | Indicators |
|---|---|
| Trend | `sma_20` `sma_50` `sma_200` `ema_9` `ema_21` `ema_50` `ema_200` `macd` `macd_signal` `macd_histogram` `adx_14` `plus_di` `minus_di` `aroon_up` `aroon_down` `vortex_plus` `vortex_minus` `supertrend` `parabolic_sar` `ichimoku_tenkan` `ichimoku_kijun` `ichimoku_senkou_a` `ichimoku_senkou_b` `linear_slope_20` |
| Momentum | `rsi_14` `rsi_7` `stochastic_k` `stochastic_d` `stoch_rsi_k` `cci_20` `williams_r` `mfi_14` `roc_10` `cmo_14` `ultimate_oscillator` `awesome_oscillator` `tsi` |
| Volatility | `atr_14` `true_range` `bollinger_upper` `bollinger_middle` `bollinger_lower` `bollinger_percent_b` `bollinger_bandwidth` `keltner_upper` `keltner_lower` `historical_volatility` `zscore_20` `donchian_upper` `donchian_lower` |
| Volume | `vwap` `obv` `chaikin_money_flow` `accumulation_distribution` `price_volume_trend` `force_index` `volume_ratio_20` |

### Fundamental ratios

| Group | Count | Ratios |
|---|---|---|
| Valuation | 12 | P/E, PEG, P/B, P/S, EV/EBITDA, EV/Sales, market cap, enterprise value, dividend yield, EPS, book value/share, DPS |
| Profitability | 11 | Gross / operating / EBITDA / net margin, ROE, ROA, ROCE, ROIC, asset turnover, equity multiplier, effective tax rate |
| Leverage | 7 | Debt/equity, debt/assets, cash, net debt, net debt/EBITDA, interest coverage, debt/capital |
| Liquidity | 12 | Current ratio, quick ratio, cash ratio, working capital, working capital/share, operating cash flow, free cash flow, FCF margin, CFO/net income, capex, CFPS, FCFPS |
| Growth | 8 | Revenue / net income / EPS / CFO YoY, revenue and net income 3-year and 5-year CAGR |
| DuPont | 4 | Net margin × asset turnover × equity multiplier, reconciled ROE |
| **Total** | **54** | plus a 0-100 health score with a per-metric breakdown |

### India-specific (Screener.in)

ROCE, ROE, book value, face value, market cap in crore, debt/equity, ROCE history,
debtor days, inventory days, days payable, cash conversion cycle, and the promoter /
FII / DII / government / public holding pattern with quarterly history.

## Indices covered

The default snapshot covers NIFTY 50, SENSEX, NIFTY BANK, NIFTY IT, NIFTY AUTO, NIFTY FMCG, NIFTY PHARMA, NIFTY REALTY, NIFTY METAL, NIFTY MEDIA, NIFTY ENERGY, NIFTY PSU BANK, NIFTY PRIVATE BANK, NIFTY FINANCIAL SERVICES, INDIA VIX.

It also accepts these names on request: NIFTY 500, NIFTY TOTAL MARKET.

One of them, the free source does not publish: Yahoo carries every index in the default
set except Nifty Private Bank, so that one is reported back under "unavailable"
rather than quietly dropped.

## Configuration

| Variable | Default |
|---|---|
| `TRADEMCP_TIMEOUT` | `30` |
| `TRADEMCP_CACHE_DIR` | `~/.cache/trademcp` |
| `TRADEMCP_QUOTE_TTL` | `300` |
| `TRADEMCP_PRICE_TTL` | `900` |
| `TRADEMCP_FUNDAMENTALS_TTL` | `21600` |
| `TRADEMCP_UNIVERSE_TTL` | `43200` |
| `TRADEMCP_PROFILE_TTL` | `86400` |
| `TRADEMCP_MAX_CONCURRENCY` | `8` |
| `TRADEMCP_ENABLE_SCREENER_IN` | `1` |

