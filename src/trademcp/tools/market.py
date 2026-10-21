"""Market data tools: symbol search, quotes, price history, indices and breadth."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from pydantic import Field

from .. import config
from ..app import mcp
from ..formatting import fmt_epoch
from ..http import DataSourceError
from ..providers import nse, yahoo
from ..symbols import ResolvedSymbol, SymbolNotFound, resolve, search_symbols
from .common import ResponseFormat, error_text, render, tool_annotations


def _fmt_field(description: str):
    return Field(description=description)


def _ticker_for(resolved: ResolvedSymbol, exchange: str) -> str:
    """Honour a BSE request by switching the Yahoo suffix."""
    if exchange.upper() == "BSE" and resolved.yahoo_ticker.endswith(".NS"):
        return f"{resolved.symbol}.BO"
    return resolved.yahoo_ticker


async def _resolve_or_error(query: str, exchange: str) -> tuple[ResolvedSymbol | None, str | None]:
    try:
        return await resolve(query, exchange), None
    except SymbolNotFound as exc:
        return None, error_text(exc)
    except DataSourceError as exc:
        return None, error_text(exc)


@mcp.tool(name="trademcp_search_symbol", annotations=tool_annotations("Search Indian symbols"))
async def trademcp_search_symbol(
    query: Annotated[
        str,
        _fmt_field("Symbol code or company name to search, e.g. 'RELIANCE', 'tata', 'bank of baroda'"),
    ],
    limit: Annotated[int, _fmt_field("Maximum results to return (1-50)")] = 15,
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' for readable output or 'json' for structured data")] = ResponseFormat.MARKDOWN,
) -> str:
    """Search NSE-listed companies by ticker symbol or company name.

    Use this when the user gives a company name rather than an NSE code, or when
    a symbol might be ambiguous. Returns the NSE code, company name, ISIN and
    listing details for each match, ranked with exact symbol matches first.

    Args:
        query: ticker or company name to search for
        limit: maximum number of matches to return
        response_format: 'markdown' or 'json'

    Returns:
        Markdown table or JSON list of matches with 'symbol', 'name', 'isin' fields.
    """
    try:
        results = await search_symbols(query, limit=min(limit, 50))
    except DataSourceError as exc:
        return error_text(exc)

    payload = {
        "query": query,
        "match_count": len(results),
        "matches": results,
    }
    return render(payload, response_format, f"Symbol search: {query}")


@mcp.tool(name="trademcp_get_quote", annotations=tool_annotations("Get live quote"))
async def trademcp_get_quote(
    symbol: Annotated[str, _fmt_field("NSE symbol or company name, e.g. 'RELIANCE' or 'tata motors'")],
    exchange: Annotated[str, _fmt_field("Preferred listing: 'NSE' or 'BSE'")] = "NSE",
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Get the latest price quote and key statistics for an Indian stock.

    Returns the last traded price, day change, day's range, volume, 52-week
    range, market capitalisation and valuation multiples (P/E, P/B, EPS,
    dividend yield, beta), plus 1 week / 1 month / 3 month / 1 year returns.

    Args:
        symbol: NSE symbol or company name
        exchange: 'NSE' or 'BSE'
        response_format: 'markdown' or 'json'

    Returns:
        Markdown or JSON quote payload. 'Error: ...' if the symbol cannot be resolved.
    """
    resolved, err = await _resolve_or_error(symbol, exchange)
    if err:
        return err

    assert resolved is not None
    ticker = _ticker_for(resolved, exchange)
    try:
        quotes = await yahoo.get_quotes([ticker])
        quote = quotes.get(ticker) or {}
        bars, _meta = await yahoo.get_bars(ticker, range_="1y", interval="1d")
    except DataSourceError as exc:
        return error_text(exc)

    if not quote and not bars:
        return error_text(DataSourceError(f"No quote data available for '{symbol}'."))

    closes = [b.close for b in bars]
    price = quote.get("regularMarketPrice") or (closes[-1] if closes else None)

    def period_return(days: int) -> float | None:
        if len(closes) <= days or not closes[-1]:
            return None
        return (closes[-1] - closes[-days - 1]) / closes[-days - 1] * 100

    high_52 = quote.get("fiftyTwoWeekHigh") or (max(b.high for b in bars) if bars else None)
    low_52 = quote.get("fiftyTwoWeekLow") or (min(b.low for b in bars) if bars else None)
    position = None
    if price and high_52 and low_52 and high_52 > low_52:
        position = (price - low_52) / (high_52 - low_52) * 100

    payload = {
        "symbol": resolved.symbol,
        "name": resolved.name or quote.get("shortName"),
        "exchange": exchange.upper(),
        "ticker": ticker,
        "industry": resolved.industry,
        "isin": resolved.isin,
        "currency": quote.get("currency", "INR"),
        "last_traded_at": fmt_epoch(quote.get("regularMarketTime")),
        "price": price,
        "change": quote.get("regularMarketChange"),
        "change_pct": quote.get("regularMarketChangePercent"),
        "open": quote.get("regularMarketOpen"),
        "day_high": quote.get("regularMarketDayHigh"),
        "day_low": quote.get("regularMarketDayLow"),
        "previous_close": quote.get("previousClose"),
        "volume": quote.get("regularMarketVolume"),
        "average_volume": quote.get("averageVolume") or quote.get("averageDailyVolume10Day"),
        "week_52_high": high_52,
        "week_52_low": low_52,
        "position_in_52w_range_pct": position,
        "market_cap": quote.get("marketCap"),
        "trailing_pe": quote.get("trailingPE"),
        "forward_pe": quote.get("forwardPE"),
        "price_to_book": quote.get("priceToBook"),
        "eps_ttm": quote.get("epsTrailingTwelveMonths"),
        "book_value": quote.get("bookValue"),
        "dividend_yield_pct": quote.get("dividendYield"),
        "beta": quote.get("beta"),
        "returns": {
            "1_week_pct": period_return(5),
            "1_month_pct": period_return(21),
            "3_month_pct": period_return(63),
            "6_month_pct": period_return(126),
            "1_year_pct": period_return(252),
        },
    }
    return render(payload, response_format, f"{resolved.symbol} - {resolved.name}")


@mcp.tool(name="trademcp_get_price_history", annotations=tool_annotations("Get OHLCV history"))
async def trademcp_get_price_history(
    symbol: Annotated[str, _fmt_field("NSE symbol or company name, e.g. 'INFY'")],
    range: Annotated[
        str,
        _fmt_field("Lookback window: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"),
    ] = "6mo",
    interval: Annotated[str, _fmt_field("Bar size: 1d, 1wk, 1mo, 1h, 30m, 15m, 5m")] = "1d",
    limit: Annotated[int, _fmt_field("Maximum number of candles to return (1-500)")] = 60,
    exchange: Annotated[str, _fmt_field("'NSE' or 'BSE'")] = "NSE",
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Get historical OHLCV candles for an Indian stock.

    Returns the most recent candles with date, open, high, low, close and
    volume, newest first, along with the period's start/end prices and total
    return so the caller can chart or analyse the series.

    Args:
        symbol: NSE symbol or company name
        range: lookback window
        interval: candle size
        limit: maximum candles to return
        exchange: 'NSE' or 'BSE'
        response_format: 'markdown' or 'json'

    Returns:
        Markdown table of candles, or JSON with 'candles' and 'period_summary'.
    """
    resolved, err = await _resolve_or_error(symbol, exchange)
    if err:
        return err

    assert resolved is not None
    ticker = _ticker_for(resolved, exchange)
    try:
        bars, meta = await yahoo.get_bars(ticker, range_=range, interval=interval)
    except DataSourceError as exc:
        return error_text(exc)

    if not bars:
        return error_text(DataSourceError(f"No price history available for '{symbol}'."))

    shown = list(reversed(bars[-limit:]))
    first, last = bars[0], bars[-1]
    payload = {
        "symbol": resolved.symbol,
        "name": resolved.name,
        "ticker": ticker,
        "range": range,
        "interval": interval,
        "currency": meta.get("currency", "INR"),
        "exchange": meta.get("exchangeName"),
        "period_summary": {
            "candles_available": len(bars),
            "from": first.date,
            "to": last.date,
            "start_close": first.close,
            "end_close": last.close,
            "period_return_pct": round((last.close - first.close) / first.close * 100, 2)
            if first.close
            else None,
            "highest": max(b.high for b in bars),
            "lowest": min(b.low for b in bars),
            "total_volume": sum(b.volume for b in bars),
        },
        "candles": [b.as_dict() for b in shown],
    }
    return render(payload, response_format, f"{resolved.symbol} price history ({range}, {interval})")


@mcp.tool(name="trademcp_get_index_snapshot", annotations=tool_annotations("Index snapshot"))
async def trademcp_get_index_snapshot(
    indices: Annotated[
        list[str] | None,
        _fmt_field("Index names to fetch, e.g. ['NIFTY 50','SENSEX','NIFTY BANK']. Omit for the default set."),
    ] = None,
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Get live quotes for major Indian indices.

    Covers NIFTY 50, SENSEX, the NIFTY sector indices (Bank, IT, Auto, FMCG,
    Pharma, Realty, Metal, Energy, PSU Bank, Private Bank, Financial Services,
    Media) and INDIA VIX, so the caller can see where the market stands.

    Args:
        indices: optional list of index names to fetch
        response_format: 'markdown' or 'json'

    Returns:
        Markdown table or JSON list of index quotes with price, change and percent change.
    """
    from ..symbols import INDEX_TICKERS

    wanted = indices or ["NIFTY 50", "SENSEX", "NIFTY BANK", "NIFTY IT", "NIFTY AUTO", "NIFTY FMCG",
                         "NIFTY PHARMA", "NIFTY REALTY", "NIFTY METAL", "NIFTY ENERGY",
                         "NIFTY PSU BANK", "NIFTY FINANCIAL SERVICES", "INDIA VIX"]

    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    for name in wanted:
        ticker = INDEX_TICKERS.get(name.upper())
        if not ticker:
            skipped.append(name)
            continue
        try:
            quote = (await yahoo.get_quotes([ticker])).get(ticker) or {}
        except DataSourceError:
            quote = {}
        if not quote:
            skipped.append(name)
            continue
        rows.append(
            {
                "index": name.upper(),
                "price": quote.get("regularMarketPrice"),
                "change": quote.get("regularMarketChange"),
                "change_pct": quote.get("regularMarketChangePercent"),
                "day_high": quote.get("regularMarketDayHigh"),
                "day_low": quote.get("regularMarketDayLow"),
                "previous_close": quote.get("previousClose"),
                "volume": quote.get("regularMarketVolume"),
            }
        )

    payload: dict[str, Any] = {"index_count": len(rows), "indices": rows}
    if skipped:
        payload["unavailable"] = skipped
    return render(payload, response_format, "Indian market index snapshot")


@mcp.tool(name="trademcp_get_market_breadth", annotations=tool_annotations("Market breadth"))
async def trademcp_get_market_breadth(
    index: Annotated[str, _fmt_field("Index whose constituents are analysed: 'NIFTY 50' or 'NIFTY 100'")] = "NIFTY 50",
    include_trend: Annotated[
        bool,
        _fmt_field("Also compute the share of constituents above their 200-day moving average (slower)"),
    ] = True,
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Measure market breadth for an Indian index.

    Counts advancers, decliners and unchanged stocks among the index
    constituents, reports the average and median move, and lists the top
    gainers and losers. Optionally adds the percentage of constituents trading
    above their 200-day moving average, the classic trend-breadth gauge.

    Args:
        index: index to analyse
        include_trend: compute the 200-day moving average breadth too
        response_format: 'markdown' or 'json'

    Returns:
        Markdown or JSON breadth summary with gainers, losers and breadth percentages.
    """
    try:
        constituents = await nse.get_index_constituents(index)
    except (KeyError, DataSourceError) as exc:
        return error_text(exc if isinstance(exc, DataSourceError) else DataSourceError(str(exc)))

    tickers = [f"{c['symbol']}.NS" for c in constituents]
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY)

    async def fetch(ticker: str) -> dict[str, Any] | None:
        async with semaphore:
            try:
                return (await yahoo.get_quotes([ticker])).get(ticker)
            except DataSourceError:
                return None

    quotes = [q for q in await asyncio.gather(*(fetch(t) for t in tickers)) if q]

    def change_pct(quote: dict[str, Any]) -> float:
        value = quote.get("regularMarketChangePercent")
        if value is None:
            prev, price = quote.get("previousClose"), quote.get("regularMarketPrice")
            value = ((price - prev) / prev * 100) if prev and price else 0.0
        return value

    ranked = sorted(quotes, key=change_pct, reverse=True)
    advances = [q for q in ranked if change_pct(q) > 0.001]
    declines = [q for q in ranked if change_pct(q) < -0.001]
    unchanged = [q for q in ranked if abs(change_pct(q)) <= 0.001]
    changes = [change_pct(q) for q in ranked]
    median = sorted(changes)[len(changes) // 2] if changes else None

    above_200 = None
    if include_trend:

        async def above_ma(ticker: str) -> bool | None:
            async with semaphore:
                try:
                    bars, _ = await yahoo.get_bars(ticker, range_="1y", interval="1d")
                except DataSourceError:
                    return None
                if len(bars) < 200:
                    return None
                ma = sum(b.close for b in bars[-200:]) / 200
                return bars[-1].close > ma

        results = await asyncio.gather(*(above_ma(t) for t in tickers))
        valid = [r for r in results if r is not None]
        above_200 = round(sum(valid) / len(valid) * 100, 1) if valid else None

    def brief(quote: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": str(quote.get("symbol", "")).split(".")[0],
            "change_pct": round(change_pct(quote), 2),
            "price": quote.get("regularMarketPrice"),
        }

    total = len(ranked)
    payload = {
        "index": index.upper(),
        "constituents_fetched": total,
        "breadth": {
            "advancers": len(advances),
            "decliners": len(declines),
            "unchanged": len(unchanged),
            "advance_decline_ratio": round(len(advances) / len(declines), 2) if declines else None,
            "advance_pct": round(len(advances) / total * 100, 1) if total else None,
            "decline_pct": round(len(declines) / total * 100, 1) if total else None,
            "average_change_pct": round(sum(changes) / len(changes), 2) if changes else None,
            "median_change_pct": round(median, 2) if median is not None else None,
            "above_200dma_pct": above_200,
        },
        "top_gainers": [brief(q) for q in ranked[:5]],
        "top_losers": [brief(q) for q in list(reversed(ranked))[:5]],
    }
    return render(payload, response_format, f"Market breadth - {index.upper()}")


@mcp.tool(name="trademcp_compare_stocks", annotations=tool_annotations("Compare stocks"))
async def trademcp_compare_stocks(
    symbols: Annotated[
        list[str],
        _fmt_field("Two to five NSE symbols or company names to compare side by side"),
    ],
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Compare two to five Indian stocks across price, valuation, quality and momentum.

    Fetches the latest quote, headline fundamental ratios and the technical
    signal score for each symbol, then lines them up so the differences are
    obvious.

    Args:
        symbols: two to five symbols or company names
        response_format: 'markdown' or 'json'

    Returns:
        Markdown table or JSON list with one row per symbol.
    """
    if not symbols or len(symbols) < 2:
        return error_text(DataSourceError("Provide at least two symbols to compare."))
    if len(symbols) > 5:
        symbols = symbols[:5]

    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for query in symbols:
        try:
            resolved = await resolve(query)
        except (SymbolNotFound, DataSourceError) as exc:
            errors.append(f"{query}: {exc}")
            continue

        row: dict[str, Any] = {
            "symbol": resolved.symbol,
            "name": resolved.name,
            "industry": resolved.industry,
        }
        try:
            ticker = resolved.yahoo_ticker
            quote = (await yahoo.get_quotes([ticker])).get(ticker) or {}
            row.update(
                {
                    "price": quote.get("regularMarketPrice"),
                    "change_pct": quote.get("regularMarketChangePercent"),
                    "market_cap": quote.get("marketCap"),
                    "pe_ratio": quote.get("trailingPE"),
                    "price_to_book": quote.get("priceToBook"),
                    "eps": quote.get("epsTrailingTwelveMonths"),
                    "dividend_yield_pct": quote.get("dividendYield"),
                    "week_52_high": quote.get("fiftyTwoWeekHigh"),
                    "week_52_low": quote.get("fiftyTwoWeekLow"),
                    "volume": quote.get("regularMarketVolume"),
                }
            )
            series = await yahoo.get_timeseries(
                ticker,
                ["annualTotalRevenue", "annualNetIncome", "annualStockholdersEquity",
                 "annualTotalDebt", "annualTotalAssets", "annualInvestedCapital", "annualEBITDA",
                 "trailingMarketCap", "trailingPeRatio"],
                years=5,
            )
            from ..analytics import fundamentals as fa

            profile = fa.build_fundamentals(series, price=row.get("price"), symbol=resolved.symbol)
            row.update(
                {
                    "roe_pct": profile["profitability"]["return_on_equity_pct"],
                    "net_margin_pct": profile["profitability"]["net_margin_pct"],
                    "debt_to_equity": profile["leverage"]["debt_to_equity"],
                    "revenue_cagr_3y_pct": profile["growth"]["revenue_cagr_3y_pct"],
                    "health_score": profile["health_score"]["score"],
                }
            )
            bars, _ = await yahoo.get_bars(ticker, range_="1y", interval="1d")
            if bars:
                from ..analytics import signals as sg

                row["technical_score"] = sg.technical_signals(bars)["summary"]["score"]
                row["technical_label"] = sg.technical_signals(bars)["summary"]["label"]
        except DataSourceError as exc:
            errors.append(f"{query}: {exc}")
        rows.append(row)

    payload: dict[str, Any] = {"compared": len(rows), "stocks": rows}
    if errors:
        payload["errors"] = errors
    return render(payload, response_format, "Stock comparison")
