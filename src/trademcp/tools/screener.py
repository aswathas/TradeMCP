"""Screening and portfolio tools."""

from __future__ import annotations

import asyncio
import time
from typing import Annotated, Any

from pydantic import BaseModel, Field

from ..analytics import fundamentals as fa
from ..analytics import indicators as ind
from ..analytics import signals as sg
from ..app import mcp
from ..http import DataSourceError
from ..providers import nse, yahoo
from ..symbols import SymbolNotFound, resolve
from .common import ResponseFormat, error_text, render, tool_annotations


def _fmt_field(description: str):
    return Field(description=description)


class Holding(BaseModel):
    """One portfolio position."""

    symbol: str = Field(..., description="NSE symbol or company name")
    quantity: float = Field(..., description="Number of shares held", gt=0)
    cost_price: float | None = Field(None, description="Average buy price per share")


async def _fetch_profiles(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fundamental profile for each symbol, fetched concurrently."""
    semaphore = asyncio.Semaphore(8)

    async def one(symbol: str) -> tuple[str, dict[str, Any] | None]:
        async with semaphore:
            try:
                series = await yahoo.get_timeseries(
                    f"{symbol}.NS",
                    yahoo.ANNUAL_TYPES + yahoo.TRAILING_TYPES,
                    years=6,
                )
                if not series:
                    return symbol, None
                return symbol, fa.build_fundamentals(series, screener=None, symbol=symbol)
            except DataSourceError:
                return symbol, None

    results = await asyncio.gather(*(one(s) for s in symbols))
    return {symbol: profile for symbol, profile in results if profile}


@mcp.tool(name="trademcp_screen_stocks", annotations=tool_annotations("Screen stocks"))
async def trademcp_screen_stocks(
    universe: Annotated[
        str,
        _fmt_field("Stock universe to scan: 'NIFTY 50', 'NIFTY 100', 'NIFTY 500' or 'NSE' (all listed)"),
    ] = "NIFTY 50",
    min_pe: Annotated[float | None, _fmt_field("Only stocks with P/E at or below this")] = None,
    max_pe: Annotated[float | None, _fmt_field("Only stocks with P/E at or above this")] = None,
    min_roe: Annotated[float | None, _fmt_field("Minimum return on equity (%)")] = None,
    min_roce: Annotated[float | None, _fmt_field("Minimum return on capital employed (%)")] = None,
    min_net_margin: Annotated[float | None, _fmt_field("Minimum net profit margin (%)")] = None,
    max_debt_to_equity: Annotated[float | None, _fmt_field("Maximum debt to equity ratio")] = None,
    min_market_cap: Annotated[float | None, _fmt_field("Minimum market cap in rupees")] = None,
    min_dividend_yield: Annotated[float | None, _fmt_field("Minimum dividend yield (%)")] = None,
    min_current_ratio: Annotated[float | None, _fmt_field("Minimum current ratio")] = None,
    min_revenue_cagr: Annotated[float | None, _fmt_field("Minimum 3-year revenue CAGR (%)")] = None,
    rsi_below: Annotated[float | None, _fmt_field("Only stocks with RSI under this (oversold screen)")] = None,
    rsi_above: Annotated[float | None, _fmt_field("Only stocks with RSI over this (overbought screen)")] = None,
    above_sma50: Annotated[bool | None, _fmt_field("Only stocks trading above their 50-day average")] = None,
    above_sma200: Annotated[bool | None, _fmt_field("Only stocks trading above their 200-day average")] = None,
    limit: Annotated[int, _fmt_field("Maximum stocks to return (1-100)")] = 20,
    sort_by: Annotated[
        str,
        _fmt_field("Sort field: 'market_cap', 'pe_ratio', 'price_to_book', 'roe_pct', 'roce_pct', 'revenue_cagr_3y_pct', 'dividend_yield_pct', 'health_score'"),
    ] = "market_cap",
    sort_order: Annotated[str, _fmt_field("Sort direction: 'desc' or 'asc'")] = "desc",
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Screen Indian stocks by fundamental and technical criteria.

    Scans an index universe (or every NSE-listed stock), pulls the latest
    fundamentals for each name, applies the fundamental filters, then applies
    the technical filters to the survivors and returns the best matches.

    Args:
        universe: 'NIFTY 50', 'NIFTY 100', 'NIFTY 500' or 'NSE'
        min_pe: maximum P/E
        max_pe: minimum P/E
        min_roe: minimum return on equity (%)
        min_roce: minimum return on capital employed (%)
        min_net_margin: minimum net margin (%)
        max_debt_to_equity: maximum debt/equity
        min_market_cap: minimum market cap in rupees
        min_dividend_yield: minimum dividend yield (%)
        min_current_ratio: minimum current ratio
        min_revenue_cagr: minimum 3-year revenue CAGR (%)
        rsi_below: maximum RSI (oversold screen)
        rsi_above: minimum RSI (overbought screen)
        above_sma50: require price above the 50-day average
        above_sma200: require price above the 200-day average
        limit: maximum rows to return
        sort_by: field to sort by
        sort_order: 'desc' (default) or 'asc'
        response_format: 'markdown' or 'json'

    Returns:
        Markdown table or JSON with 'matches' and the filter set applied.
    """
    started = time.time()

    try:
        if universe.upper() == "NSE":
            master = await nse.get_equity_master()
            symbols = list(master.keys())
        else:
            constituents = await nse.get_index_constituents(universe)
            symbols = [c["symbol"] for c in constituents]
    except (KeyError, DataSourceError) as exc:
        return error_text(exc if isinstance(exc, DataSourceError) else DataSourceError(str(exc)))

    if not symbols:
        return error_text(DataSourceError(f"No symbols found for universe '{universe}'."))

    scanned = len(symbols)
    if scanned > 600:
        symbols = symbols[:600]

    profiles = await _fetch_profiles(symbols)

    # One batched quote call per 40 symbols fills in dividend yield and live multiples.
    quote_map: dict[str, dict[str, Any]] = {}
    try:
        quote_map = await yahoo.get_quotes([f"{s}.NS" for s in symbols])
    except DataSourceError:
        quote_map = {}

    def dividend_yield(symbol: str, valuation: dict[str, Any]) -> float | None:
        """Dividend yield in percent - live quote first, fundamentals second."""
        quote = quote_map.get(f"{symbol}.NS") or {}
        value = quote.get("dividendYield")
        if value is None:
            value = valuation.get("dividend_yield_pct")
        return float(value) if value is not None else None

    def keep(symbol: str, profile: dict[str, Any]) -> bool:
        valuation = profile["valuation"]
        profitability = profile["profitability"]
        leverage = profile["leverage"]
        liquidity = profile["liquidity"]
        growth = profile["growth"]

        pe = valuation.get("pe_ratio")
        if min_pe is not None and (pe is None or pe > min_pe):
            return False
        if max_pe is not None and (pe is None or pe < max_pe):
            return False
        if min_roe is not None:
            roe = profitability.get("return_on_equity_pct")
            if roe is None or roe < min_roe:
                return False
        if min_roce is not None:
            roce = profitability.get("roce_pct")
            if roce is None or roce < min_roce:
                return False
        if min_net_margin is not None:
            margin = profitability.get("net_margin_pct")
            if margin is None or margin < min_net_margin:
                return False
        if max_debt_to_equity is not None:
            debt_equity = leverage.get("debt_to_equity")
            if debt_equity is None or debt_equity > max_debt_to_equity:
                return False
        if min_market_cap is not None:
            cap = valuation.get("market_cap")
            if cap is None or cap < min_market_cap:
                return False
        if min_dividend_yield is not None:
            dividend = dividend_yield(symbol, valuation)
            if dividend is None or dividend < min_dividend_yield:
                return False
        if min_current_ratio is not None:
            ratio = liquidity.get("current_ratio")
            if ratio is None or ratio < min_current_ratio:
                return False
        if min_revenue_cagr is not None:
            cagr = growth.get("revenue_cagr_3y_pct")
            if cagr is None or cagr < min_revenue_cagr:
                return False
        return True

    passed = [
        (symbol, profile)
        for symbol, profile in profiles.items()
        if keep(symbol, profile)
    ]

    needs_technicals = (
        rsi_below is not None
        or rsi_above is not None
        or above_sma50 is not None
        or above_sma200 is not None
    )

    technical_map: dict[str, dict[str, Any]] = {}
    if needs_technicals and passed:
        semaphore = asyncio.Semaphore(8)

        async def tech(symbol: str) -> tuple[str, dict[str, Any] | None]:
            async with semaphore:
                try:
                    bars, _ = await yahoo.get_bars(f"{symbol}.NS", range_="1y", interval="1d")
                except DataSourceError:
                    return symbol, None
                if len(bars) < 60:
                    return symbol, None
                closes = [b.close for b in bars]
                return symbol, {
                    "rsi_14": sg._last(ind.rsi(closes, 14)),
                    "sma_50": sg._last(ind.sma(closes, 50)),
                    "sma_200": sg._last(ind.sma(closes, 200)),
                    "price": closes[-1],
                }

        for symbol, data in await asyncio.gather(*(tech(s) for s, _ in passed)):
            if data:
                technical_map[symbol] = data

    rows: list[dict[str, Any]] = []
    for symbol, profile in passed:
        quote = quote_map.get(f"{symbol}.NS") or {}
        row: dict[str, Any] = {
            "symbol": symbol,
            "price": quote.get("regularMarketPrice"),
            "market_cap": quote.get("marketCap") or profile["valuation"].get("market_cap"),
            "pe_ratio": quote.get("trailingPE") or profile["valuation"].get("pe_ratio"),
            "price_to_book": quote.get("priceToBook") or profile["valuation"].get("price_to_book"),
            "ev_to_ebitda": profile["valuation"].get("ev_to_ebitda"),
            "roe_pct": profile["profitability"].get("return_on_equity_pct"),
            "roce_pct": profile["profitability"].get("roce_pct"),
            "net_margin_pct": profile["profitability"].get("net_margin_pct"),
            "debt_to_equity": profile["leverage"].get("debt_to_equity"),
            "current_ratio": profile["liquidity"].get("current_ratio"),
            "revenue_cagr_3y_pct": profile["growth"].get("revenue_cagr_3y_pct"),
            "dividend_yield_pct": dividend_yield(symbol, profile["valuation"]),
            "health_score": profile["health_score"]["score"],
        }
        tech = technical_map.get(symbol)
        if tech:
            row.update({"price": tech["price"], "rsi_14": tech["rsi_14"]})
            if above_sma50 is not None:
                if tech["sma_50"] is None or not ((tech["price"] > tech["sma_50"]) == above_sma50):
                    continue
            if above_sma200 is not None:
                if tech["sma_200"] is None or not ((tech["price"] > tech["sma_200"]) == above_sma200):
                    continue
            if rsi_below is not None and (tech["rsi_14"] is None or tech["rsi_14"] > rsi_below):
                continue
            if rsi_above is not None and (tech["rsi_14"] is None or tech["rsi_14"] < rsi_above):
                continue
        rows.append(row)

    key = sort_by if (rows and sort_by in rows[0]) else "market_cap"
    reverse = sort_order.lower() != "asc"
    rows.sort(key=lambda r: (r.get(key) is not None, r.get(key)), reverse=reverse)
    rows = rows[:limit]

    payload = {
        "universe": universe.upper(),
        "symbols_scanned": scanned,
        "with_fundamentals": len(profiles),
        "passed_fundamental_filters": len(passed),
        "final_matches": len(rows),
        "filters": {
            "min_pe": min_pe,
            "max_pe": max_pe,
            "min_roe": min_roe,
            "min_roce": min_roce,
            "min_net_margin": min_net_margin,
            "max_debt_to_equity": max_debt_to_equity,
            "min_market_cap": min_market_cap,
            "min_dividend_yield": min_dividend_yield,
            "min_current_ratio": min_current_ratio,
            "min_revenue_cagr": min_revenue_cagr,
            "rsi_below": rsi_below,
            "rsi_above": rsi_above,
            "above_sma50": above_sma50,
            "above_sma200": above_sma200,
        },
        "elapsed_seconds": round(time.time() - started, 1),
        "matches": rows,
    }
    return render(payload, response_format, f"Stock screen - {universe.upper()}")


@mcp.tool(name="trademcp_analyze_portfolio", annotations=tool_annotations("Analyse portfolio"))
async def trademcp_analyze_portfolio(
    holdings: Annotated[
        list[Holding],
        _fmt_field("Positions to analyse, e.g. [{'symbol':'RELIANCE','quantity':10,'cost_price':1200}]"),
    ],
    benchmark: Annotated[str, _fmt_field("Benchmark index: 'NIFTY 50' or 'SENSEX'")] = "NIFTY 50",
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Analyse an Indian equity portfolio.

    Values every holding at the latest price, computes profit and loss, weight
    and sector concentration, adds each stock's technical signal, then measures
    the portfolio against the benchmark (beta, annualised volatility, Sharpe,
    max drawdown) and flags concentration or signal risk.

    Args:
        holdings: list of positions with symbol, quantity and optional cost price
        benchmark: benchmark index for risk metrics
        response_format: 'markdown' or 'json'

    Returns:
        Markdown or JSON with 'holdings', 'allocation', 'risk', 'performance' and 'flags'.
    """
    if not holdings:
        return error_text(DataSourceError("Provide at least one holding."))
    if len(holdings) > 50:
        holdings = holdings[:50]

    from ..symbols import INDEX_TICKERS

    resolved_items: list[dict[str, Any]] = []
    errors: list[str] = []
    for holding in holdings:
        try:
            resolved = await resolve(holding.symbol)
        except (SymbolNotFound, DataSourceError) as exc:
            errors.append(f"{holding.symbol}: {exc}")
            continue
        resolved_items.append({"holding": holding, "resolved": resolved})

    if not resolved_items:
        return error_text(DataSourceError("None of the holdings could be resolved."))

    semaphore = asyncio.Semaphore(8)

    async def load(item: dict[str, Any]) -> dict[str, Any] | None:
        resolved = item["resolved"]
        async with semaphore:
            try:
                quote = (await yahoo.get_quotes([resolved.yahoo_ticker])).get(resolved.yahoo_ticker) or {}
                bars, _ = await yahoo.get_bars(resolved.yahoo_ticker, range_="1y", interval="1d")
            except DataSourceError:
                return None
        return {"item": item, "quote": quote, "bars": bars}

    loaded = [d for d in await asyncio.gather(*(load(i) for i in resolved_items)) if d]

    total_value = 0.0
    total_cost = 0.0
    position_rows: list[dict[str, Any]] = []

    for data in loaded:
        holding = data["item"]["holding"]
        resolved = data["item"]["resolved"]
        quote = data["quote"]
        bars = data["bars"]
        price = quote.get("regularMarketPrice") or (bars[-1].close if bars else None)
        if price is None:
            errors.append(f"{resolved.symbol}: no price available")
            continue

        value = price * holding.quantity
        cost = (holding.cost_price or price) * holding.quantity
        total_value += value
        total_cost += cost

        technical = sg.technical_signals(bars) if len(bars) >= 30 else None
        high_52 = quote.get("fiftyTwoWeekHigh") or (max(b.high for b in bars) if bars else None)
        row = {
            "symbol": resolved.symbol,
            "name": resolved.name,
            "industry": resolved.industry,
            "quantity": holding.quantity,
            "cost_price": holding.cost_price,
            "current_price": price,
            "market_value": value,
            "profit_loss": value - cost,
            "profit_loss_pct": round((value - cost) / cost * 100, 2) if cost else None,
            "technical_score": technical["summary"]["score"] if technical else None,
            "technical_label": technical["summary"]["label"] if technical else None,
            "rsi_14": technical["indicators"]["rsi_14"] if technical else None,
            "distance_from_52w_high_pct": round((price - high_52) / high_52 * 100, 2) if high_52 else None,
            "bars": bars,
        }
        position_rows.append(row)

    for row in position_rows:
        row["weight_pct"] = round(row["market_value"] / total_value * 100, 2) if total_value else None
        row.pop("bars", None)

    sector_weights: dict[str, float] = {}
    for row in position_rows:
        sector = row.get("industry") or "Unclassified"
        sector_weights[sector] = sector_weights.get(sector, 0.0) + (row.get("weight_pct") or 0.0)
    sector_weights = {k: round(v, 2) for k, v in sorted(sector_weights.items(), key=lambda kv: -kv[1])}

    # Portfolio-level risk against the benchmark
    benchmark_bars: list[Any] = []
    ticker = INDEX_TICKERS.get(benchmark.upper(), INDEX_TICKERS["NIFTY 50"])
    try:
        benchmark_bars, _ = await yahoo.get_bars(ticker, range_="1y", interval="1d")
    except DataSourceError:
        benchmark_bars = []

    risk: dict[str, Any] = {}
    dates: list[str] = []
    portfolio_series: list[float] = []
    if loaded and benchmark_bars:
        bench_by_date = {b.date: b.close for b in benchmark_bars}
        shares: dict[str, float] = {}
        for data in loaded:
            bars = data["bars"]
            if bars:
                shares[data["item"]["resolved"].symbol] = data["item"]["holding"].quantity

        series_map: dict[str, dict[str, float]] = {}
        for data in loaded:
            symbol = data["item"]["resolved"].symbol
            series_map[symbol] = {b.date: b.close for b in data["bars"]}
        common = sorted(set(bench_by_date) & set.intersection(*(set(s) for s in series_map.values()))) if series_map else []
        if len(common) > 60:
            dates = common
            for d in common:
                portfolio_series.append(sum(series_map[s][d] * shares[s] for s in series_map))
            bench_series = [bench_by_date[d] for d in common]
            beta, alpha = ind.beta_alpha(portfolio_series, bench_series)
            returns = ind.daily_returns(portfolio_series)[1:]
            sd = ind.stdev(returns, len(returns))
            risk = {
                "beta": round(beta, 2) if beta is not None else None,
                "annualised_alpha_pct": round(alpha, 2) if alpha is not None else None,
                "annualised_volatility_pct": round(sd[-1] * (252 ** 0.5) * 100, 2) if sd[-1] else None,
                "sharpe_ratio": round(ind.sharpe_ratio(portfolio_series) or 0, 2),
                "sortino_ratio": round(ind.sortino_ratio(portfolio_series) or 0, 2),
                "max_drawdown_pct": round(ind.max_drawdown(portfolio_series)["max_drawdown_pct"] or 0, 2),
                "benchmark": benchmark.upper(),
                "benchmark_return_pct": round((bench_series[-1] / bench_series[0] - 1) * 100, 2),
                "portfolio_return_pct": round((portfolio_series[-1] / portfolio_series[0] - 1) * 100, 2),
                "days_compared": len(common),
            }
            if risk["benchmark_return_pct"]:
                risk["excess_return_pct"] = round(
                    risk["portfolio_return_pct"] - risk["benchmark_return_pct"], 2
                )

    flags: list[str] = []
    for sector, weight in sector_weights.items():
        if weight > 40:
            flags.append(f"{sector} is {weight}% of the portfolio - concentration risk.")
    for row in position_rows:
        if row.get("technical_label") in ("Strong Sell", "Sell"):
            flags.append(f"{row['symbol']} carries a {row['technical_label']} technical signal.")
        if (row.get("weight_pct") or 0) > 30:
            flags.append(f"{row['symbol']} is {row['weight_pct']}% of the portfolio - single-stock concentration.")
    if risk.get("beta") is not None and risk["beta"] > 1.3:
        flags.append(f"Portfolio beta of {risk['beta']} amplifies index moves.")
    if len(position_rows) < 4:
        flags.append("Fewer than 4 holdings - limited diversification.")

    by_value = sorted(position_rows, key=lambda r: r.get("market_value") or 0, reverse=True)
    by_pnl = sorted(position_rows, key=lambda r: r.get("profit_loss") or 0, reverse=True)
    payload: dict[str, Any] = {
        "holdings_count": len(position_rows),
        "total_market_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_profit_loss": round(total_value - total_cost, 2),
        "total_profit_loss_pct": round((total_value - total_cost) / total_cost * 100, 2) if total_cost else None,
        "holdings": position_rows,
        "allocation": {
            "sector_weights_pct": sector_weights,
            "largest_position": by_value[0]["symbol"] if by_value else None,
            "largest_position_weight_pct": by_value[0].get("weight_pct") if by_value else None,
            "best_performer": by_pnl[0]["symbol"] if by_pnl else None,
            "best_performer_profit_pct": by_pnl[0].get("profit_loss_pct") if by_pnl else None,
            "worst_performer": by_pnl[-1]["symbol"] if by_pnl else None,
            "worst_performer_profit_pct": by_pnl[-1].get("profit_loss_pct") if by_pnl else None,
        },
        "risk": risk,
        "flags": flags or ["No concentration or signal flags raised."],
    }
    if errors:
        payload["errors"] = errors
    return render(payload, response_format, "Portfolio analysis")
