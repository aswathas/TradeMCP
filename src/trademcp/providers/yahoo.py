"""Yahoo Finance provider - keyless access to prices, quotes and fundamentals.

Yahoo guards the quote/summary endpoints behind a cookie + crumb pair. The
crumb flow is cheap and public, so we do it once per process and reuse it.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

import httpx

from .. import config
from ..cache import cache
from ..http import DataSourceError, get_client, get_json

_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
_SERIES_URL = "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}"
_SUMMARY_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"

ANNUAL_TYPES = [
    "annualTotalRevenue", "annualOperatingRevenue", "annualGrossProfit", "annualCostOfRevenue",
    "annualTotalExpenses", "annualEBITDA", "annualOperatingIncome", "annualNetIncome",
    "annualNetIncomeCommonStockholders", "annualDilutedEPS", "annualBasicEPS", "annualTotalAssets",
    "annualTotalDebt", "annualStockholdersEquity", "annualInvestedCapital", "annualWorkingCapital",
    "annualOperatingCashFlow", "annualFreeCashFlow", "annualCapitalExpenditure",
    "annualGrossMargins", "annualOperatingMargins", "annualProfitMargins",
    "annualReturnOnAssets", "annualReturnOnEquity", "annualDividendPerShare", "annualPayoutRatio",
    "annualBasicAverageShares", "annualDilutedAverageShares", "annualTotalRevenueGrowth",
    "annualDilutedEPSGrowth", "annualInterestExpense", "annualPretaxIncome", "annualTaxProvision",
    "annualCurrentAssets", "annualCurrentLiabilities", "annualCashAndCashEquivalents",
    "annualInventory", "annualReceivables", "annualTotalNonCurrentAssets",
    "annualTotalLiabilitiesNetMinorityInterest", "annualTotalNonCurrentLiabilitiesNetMinorityInterest",
    "annualReconciledDepreciation", "annualNormalizedEBITDA",
]

QUARTERLY_TYPES = [
    "quarterlyTotalRevenue", "quarterlyGrossProfit", "quarterlyOperatingIncome", "quarterlyNetIncome",
    "quarterlyDilutedEPS", "quarterlyTotalDebt", "quarterlyStockholdersEquity", "quarterlyTotalAssets",
    "quarterlyOperatingCashFlow", "quarterlyFreeCashFlow", "quarterlyGrossMargins",
    "quarterlyOperatingMargins", "quarterlyProfitMargins", "quarterlyEBITDA",
    "quarterlyOperatingRevenue", "quarterlyCurrentAssets", "quarterlyCurrentLiabilities",
    "quarterlyCashAndCashEquivalents", "quarterlyInvestedCapital",
    "quarterlyTotalLiabilitiesNetMinorityInterest",
]

TRAILING_TYPES = [
    "trailingMarketCap", "trailingPeRatio", "trailingPegRatio", "trailingPriceToSales",
    "trailingEnterprisesValue", "trailingEnterprisesValueEBITDARatio", "trailingReturnOnEquity",
    "trailingReturnOnAssets", "trailingProfitMargins", "trailingOperatingMargins",
    "trailingGrossMargins", "trailingEbitdaMargins", "trailingDebtToEquity", "trailingDividendYield",
    "trailingEps", "trailingEbitda", "trailingTotalRevenue", "trailingOperatingRevenue",
    "trailingGrossProfit", "trailingNetIncomeToCommon", "trailingTotalDebt",
    "trailingStockholdersEquity", "trailingTotalAssets", "trailingCurrentRatio", "trailingQuickRatio",
    "trailingTaxRate", "trailingInterestCoverage", "trailingSharesOutstanding",
    "trailingFloatShares", "trailingBeta", "trailingTotalRevenueGrowth", "trailingNetIncomeGrowth",
    "trailingOperatingCashFlow", "trailingTotalExpenses",
]

_crumb: str | None = None
_crumb_lock = asyncio.Lock()


@dataclass(slots=True)
class Bar:
    """One daily/intraday candle."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "adj_close": self.adj_close,
        }


async def _get_crumb() -> str:
    """Fetch (and memoise) the Yahoo session crumb required by quote/summary."""
    global _crumb
    if _crumb:
        return _crumb
    async with _crumb_lock:
        if _crumb:
            return _crumb
        client = await get_client()
        try:
            await client.get("https://fc.yahoo.com")  # sets the consent cookies
        except Exception:
            pass
        try:
            resp = await client.get("https://query1.finance.yahoo.com/v1/test/getcrumb")
        except httpx.TransportError as exc:
            raise DataSourceError(
                f"Yahoo Finance: crumb request failed ({type(exc).__name__}). "
                "The network may be flaky - retry shortly."
            ) from exc
        if resp.status_code != 200:
            raise DataSourceError(
                f"Yahoo Finance: could not obtain a session crumb (HTTP {resp.status_code}). Try again shortly."
            )
        _crumb = resp.text.strip()
        if not _crumb:
            raise DataSourceError("Yahoo Finance: empty session crumb. Try again shortly.")
        return _crumb


def _epoch(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


async def get_bars(
    symbol: str,
    *,
    range_: str = "1y",
    interval: str = "1d",
    period1: str | None = None,
    period2: str | None = None,
    use_cache: bool = True,
) -> tuple[list[Bar], dict[str, Any]]:
    """Return (candles, chart metadata) for a Yahoo ticker such as ``RELIANCE.NS``."""
    params: dict[str, Any] = {"interval": interval, "includePrePost": "false", "events": "div,split"}
    if period1 and period2:
        params["period1"] = _epoch(period1)
        params["period2"] = _epoch(period2)
    else:
        params["range"] = range_

    cache_key = f"chart:{symbol}:{sorted(params.items())}"
    if use_cache:
        cached = await cache.get(cache_key, config.PRICE_TTL)
        if cached:
            return [_bar_from_dict(b) for b in cached["bars"]], cached["meta"]

    data = await get_json(_CHART_URL.format(symbol=symbol), params, source=f"Yahoo Finance chart ({symbol})")
    chart = data.get("chart") or {}
    if chart.get("error"):
        raise DataSourceError(f"Yahoo Finance: {symbol} - {chart['error'].get('description', 'error')}")
    results = chart.get("result") or []
    if not results:
        raise DataSourceError(
            f"Yahoo Finance: no data for '{symbol}'. Check the ticker, or use trademcp_search_symbol to resolve it."
        )

    result = results[0]
    meta = result.get("meta") or {}
    stamps = result.get("timestamp") or []
    quote_blocks = ((result.get("indicators") or {}).get("quote") or [{}])
    quote = quote_blocks[0] if quote_blocks else {}
    adj_blocks = ((result.get("indicators") or {}).get("adjclose") or [{}])
    adj = (adj_blocks[0] or {}).get("adjclose") if adj_blocks else None

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    bars: list[Bar] = []
    for i, ts in enumerate(stamps):
        def at(seq: list[Any], default: Any = None) -> Any:
            return seq[i] if i < len(seq) else default

        close = at(closes)
        if close is None:
            continue  # holiday / halted session
        day = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        bars.append(
            Bar(
                date=day,
                open=float(at(opens, close) or close),
                high=float(at(highs, close) or close),
                low=float(at(lows, close) or close),
                close=float(close),
                volume=int(at(volumes, 0) or 0),
                adj_close=(float(at(adj, close)) if adj and at(adj) is not None else None),
            )
        )

    if use_cache:
        await cache.set(cache_key, {"bars": [b.as_dict() for b in bars], "meta": meta})

    return bars, meta


def _bar_from_dict(raw: dict[str, Any]) -> Bar:
    return Bar(
        date=raw["date"],
        open=raw["open"],
        high=raw["high"],
        low=raw["low"],
        close=raw["close"],
        volume=raw["volume"],
        adj_close=raw.get("adj_close"),
    )


async def get_quotes(symbols: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Live/delayed quotes for Yahoo tickers. Falls back to chart metadata.

    Symbols are requested in batches so a whole index can be quoted in a
    handful of calls rather than one call per stock.
    """
    tickers = list(dict.fromkeys(symbols))
    if not tickers:
        return {}

    quotes: dict[str, dict[str, Any]] = {}
    missing: list[str] = []

    for start in range(0, len(tickers), 40):
        chunk = tickers[start : start + 40]
        cached = await cache.get(f"quote:{','.join(chunk)}", config.QUOTE_TTL)
        if cached:
            quotes.update(cached)
            continue
        try:
            crumb = await _get_crumb()
            data = await get_json(
                _QUOTE_URL,
                {"symbols": ",".join(chunk), "crumb": crumb},
                source="Yahoo Finance quote",
            )
            results = (data.get("quoteResponse") or {}).get("result") or []
            batch = {r["symbol"]: r for r in results if r.get("symbol")}
            if batch:
                quotes.update(batch)
                await cache.set(f"quote:{','.join(chunk)}", batch)
            missing.extend(t for t in chunk if t not in batch)
        except DataSourceError:
            missing.extend(chunk)

    if missing:
        quotes.update(await _quotes_from_chart(missing))

    return quotes


async def _quotes_from_chart(tickers: list[str]) -> dict[str, dict[str, Any]]:
    """Fallback: derive a quote from the most recent chart bar."""
    fallback: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        try:
            bars, meta = await get_bars(ticker, range_="5d", interval="1d")
        except DataSourceError:
            continue
        if not bars:
            continue
        last = bars[-1]
        prev = bars[-2].close if len(bars) > 1 else last.close
        fallback[ticker] = {
            "symbol": ticker,
            "shortName": meta.get("shortName") or meta.get("longName"),
            "regularMarketPrice": last.close,
            "regularMarketOpen": last.open,
            "regularMarketDayHigh": last.high,
            "regularMarketDayLow": last.low,
            "previousClose": prev,
            "regularMarketChange": last.close - prev,
            "regularMarketChangePercent": ((last.close - prev) / prev * 100) if prev else None,
            "regularMarketVolume": last.volume,
            "currency": meta.get("currency"),
            "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow"),
            "exchangeName": meta.get("exchangeName"),
            "regularMarketTime": meta.get("regularMarketTime"),
        }
    return fallback


def _timeseries_cache_key(symbol: str, wanted: Sequence[str], years: int) -> str:
    """A process-stable cache key for a fundamentals request.

    ``hash()`` of strings is salted per process (PEP 456), so a hash-based key
    never survives a restart and the disk cache never hits. A truncated
    sha256 of the metric names is stable everywhere.
    """
    digest = hashlib.sha256(",".join(sorted(wanted)).encode("utf-8")).hexdigest()[:16]
    return f"ts:{symbol}:{digest}:{years}"


async def get_timeseries(
    symbol: str,
    types: Iterable[str],
    *,
    years: int = 8,
    use_cache: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """Fundamental time series (annual/quarterly/trailing) keyed by metric type."""
    wanted = sorted(set(types))
    if not wanted:
        return {}

    # A stable digest, not hash(): string hashing is salted per process, so a
    # hash()-based key never survives a restart and the disk cache never hits.
    cache_key = _timeseries_cache_key(symbol, wanted, years)
    if use_cache:
        cached = await cache.get(cache_key, config.FUNDAMENTALS_TTL)
        if cached:
            return cached

    now = int(datetime.now(tz=timezone.utc).timestamp())
    params = {
        "symbol": symbol,
        "type": ",".join(wanted),
        "period1": now - years * 365 * 24 * 3600,
        "period2": now + 24 * 3600,
        "merge": "false",
    }
    data = await get_json(
        _SERIES_URL.format(symbol=symbol), params, source=f"Yahoo Finance fundamentals ({symbol})"
    )
    ts = (data.get("timeseries") or {}).get("result") or []

    out: dict[str, list[dict[str, Any]]] = {}
    for item in ts:
        meta = item.get("meta") or {}
        type_list = meta.get("type") or []
        name = type_list[0] if isinstance(type_list, list) and type_list else None
        if not name:
            continue
        points: list[dict[str, Any]] = []
        for point in item.get(name) or []:
            reported = point.get("reportedValue")
            raw = reported.get("raw") if isinstance(reported, dict) else reported
            if raw is None:
                continue
            points.append(
                {
                    "date": point.get("asOfDate"),
                    "period_type": point.get("periodType"),
                    "value": raw,
                    "currency": point.get("currencyCode"),
                }
            )
        if points:
            out[name] = points

    if use_cache:
        await cache.set(cache_key, out)
    return out


async def get_summary(symbol: str, modules: str = "summaryDetail,defaultKeyStatistics,financialData,price") -> dict[str, Any]:
    """quoteSummary modules for a ticker (valuation, stats, profile)."""
    crumb = await _get_crumb()
    data = await get_json(
        _SUMMARY_URL.format(symbol=symbol),
        {"modules": modules, "crumb": crumb},
        source=f"Yahoo Finance summary ({symbol})",
    )
    results = (data.get("quoteSummary") or {}).get("result") or []
    return results[0] if results else {}


async def search(query: str, count: int = 10) -> list[dict[str, Any]]:
    """Search Yahoo for a symbol or company name."""
    data = await get_json(
        _SEARCH_URL,
        {"q": query, "quotesCount": count, "newsCount": 0, "listsCount": 0},
        source="Yahoo Finance search",
    )
    out: list[dict[str, Any]] = []
    for q in data.get("quotes") or []:
        out.append(
            {
                "symbol": q.get("symbol"),
                "name": q.get("shortname") or q.get("longname"),
                "exchange": q.get("exchDisp") or q.get("exchange"),
                "quote_type": q.get("quoteType"),
                "type": q.get("typeDisp"),
            }
        )
    return out
