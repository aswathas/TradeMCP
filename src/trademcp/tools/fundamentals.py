"""Fundamental analysis tools: ratios, statements and valuation."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from ..analytics import fundamentals as fa
from ..app import mcp
from ..http import DataSourceError
from ..providers import screener as screener_provider
from ..providers import yahoo
from ..symbols import SymbolNotFound, resolve
from .common import ResponseFormat, error_text, render, tool_annotations


def _fmt_field(description: str):
    return Field(description=description)


async def _load_fundamentals(symbol: str, years: int = 8) -> tuple[Any, dict[str, Any], float | None]:
    """Resolve, fetch statements, quote and the optional Screener.in profile."""
    resolved = await resolve(symbol)
    ticker = resolved.yahoo_ticker

    series = await yahoo.get_timeseries(
        ticker,
        yahoo.ANNUAL_TYPES + yahoo.QUARTERLY_TYPES + yahoo.TRAILING_TYPES,
        years=years,
    )
    quotes = await yahoo.get_quotes([ticker])
    quote = quotes.get(ticker) or {}
    price = quote.get("regularMarketPrice")
    if price is None:
        try:
            bars, _ = await yahoo.get_bars(ticker, range_="5d", interval="1d")
            price = bars[-1].close if bars else None
        except DataSourceError:
            price = None

    profile = await screener_provider.safe_company_profile(resolved.symbol)
    return resolved, {"series": series, "quote": quote, "screener": profile}, price


@mcp.tool(name="trademcp_get_fundamentals", annotations=tool_annotations("Fundamental profile"))
async def trademcp_get_fundamentals(
    symbol: Annotated[str, _fmt_field("NSE symbol or company name, e.g. 'HDFCBANK'")],
    include_india_metrics: Annotated[
        bool,
        _fmt_field("Include India-specific ratios from Screener.in (ROCE, ROCE, promoter holding, working-capital days)"),
    ] = True,
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Get a full fundamental picture of an Indian stock.

    Returns valuation (P/E, P/B, P/S, EV/EBITDA, market cap, dividend yield),
    profitability (gross/operating/net margin, ROE, ROA, ROCE, ROIC, asset
    turnover), leverage (debt/equity, net debt/EBITDA, interest coverage),
    liquidity (current ratio, quick ratio, free cash flow), growth (YoY and
    3/5-year CAGR), a DuPont breakdown and a 0-100 health score.

    Args:
        symbol: NSE symbol or company name
        include_india_metrics: pull India-specific ratios from Screener.in
        response_format: 'markdown' or 'json'

    Returns:
        Markdown or JSON with 'valuation', 'profitability', 'leverage',
        'liquidity', 'growth', 'dupont', 'india_specific' and 'health_score'.
    """
    try:
        resolved, bundle, price = await _load_fundamentals(symbol)
    except (SymbolNotFound, DataSourceError) as exc:
        return error_text(exc)

    screener_profile = bundle["screener"] if include_india_metrics else None
    profile = fa.build_fundamentals(
        bundle["series"], price=price, screener=screener_profile, symbol=resolved.symbol
    )
    profile["name"] = resolved.name
    profile["ticker"] = resolved.yahoo_ticker
    profile["industry"] = resolved.industry
    profile["isin"] = resolved.isin
    quote = bundle["quote"] or {}
    if quote:
        profile["market"] = {
            "price": quote.get("regularMarketPrice"),
            "change_pct": quote.get("regularMarketChangePercent"),
            "market_cap": quote.get("marketCap"),
            "52_week_high": quote.get("fiftyTwoWeekHigh"),
            "52_week_low": quote.get("fiftyTwoWeekLow"),
            "volume": quote.get("regularMarketVolume"),
        }
    return render(profile, response_format, f"{resolved.symbol} fundamentals")


@mcp.tool(name="trademcp_get_valuation", annotations=tool_annotations("Valuation metrics"))
async def trademcp_get_valuation(
    symbol: Annotated[str, _fmt_field("NSE symbol or company name, e.g. 'BAJFINANCE'")],
    peers: Annotated[
        bool,
        _fmt_field("Also fetch a small peer set from the same NSE industry for comparison"),
    ] = False,
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Get a focused valuation sheet for an Indian stock.

    Returns market cap, enterprise value, P/E, P/B, P/S, EV/EBITDA, PEG,
    dividend yield, EPS and book value per share, alongside a plain-English
    reading of whether the stock looks cheap or expensive versus its own
    growth and quality metrics.

    Args:
        symbol: NSE symbol or company name
        peers: include a same-industry peer comparison
        response_format: 'markdown' or 'json'

    Returns:
        Markdown or JSON with 'valuation', 'growth_context', 'verdict' and optional 'peers'.
    """
    try:
        resolved, bundle, price = await _load_fundamentals(symbol)
    except (SymbolNotFound, DataSourceError) as exc:
        return error_text(exc)

    profile = fa.build_fundamentals(
        bundle["series"], price=price, screener=bundle["screener"], symbol=resolved.symbol
    )
    valuation = profile["valuation"]
    growth = profile["growth"]
    profitability = profile["profitability"]

    notes: list[str] = []
    pe = valuation.get("pe_ratio")
    if pe is None:
        notes.append("No P/E available - the company may be loss-making.")
    else:
        if pe < 15:
            notes.append(f"P/E of {pe:.1f} sits below the usual large-cap Indian band (15-30).")
        elif pe > 35:
            notes.append(f"P/E of {pe:.1f} is well above the usual large-cap band (15-30).")
        else:
            notes.append(f"P/E of {pe:.1f} is inside the usual large-cap band (15-30).")

    cagr = growth.get("revenue_cagr_3y_pct")
    if cagr is not None:
        notes.append(f"3-year revenue CAGR is {cagr:.1f}%.")
    roe = profitability.get("return_on_equity_pct")
    if roe is not None:
        notes.append(f"ROE is {roe:.1f}% - {'healthy' if roe >= 15 else 'modest'} for a listed company.")
    debt_equity = profile["leverage"].get("debt_to_equity")
    if debt_equity is not None:
        notes.append(
            f"Debt/equity is {debt_equity:.2f} - {'conservative' if debt_equity < 0.5 else 'leveraged'}."
        )

    payload = {
        "symbol": resolved.symbol,
        "name": resolved.name,
        "industry": resolved.industry,
        "price": price,
        "valuation": valuation,
        "growth_context": {
            "revenue_cagr_3y_pct": cagr,
            "net_income_cagr_3y_pct": growth.get("net_income_cagr_3y_pct"),
            "return_on_equity_pct": roe,
            "net_margin_pct": profitability.get("net_margin_pct"),
        },
        "verdict": notes,
    }

    if peers and resolved.industry:
        from ..providers import nse

        try:
            constituents = await nse.get_index_constituents("NIFTY 500")
            same = [c for c in constituents if c["industry"] == resolved.industry][:4]
            peer_rows = []
            for peer in same:
                if peer["symbol"] == resolved.symbol:
                    continue
                try:
                    peer_series = await yahoo.get_timeseries(
                        f"{peer['symbol']}.NS",
                        ["trailingPeRatio", "trailingMarketCap", "annualTotalRevenue",
                         "annualNetIncome", "annualStockholdersEquity", "annualTotalDebt"],
                        years=5,
                    )
                    peer_profile = fa.build_fundamentals(
                        peer_series, screener=None, symbol=peer["symbol"]
                    )
                    peer_rows.append(
                        {
                            "symbol": peer["symbol"],
                            "company": peer["company"],
                            "pe_ratio": peer_profile["valuation"].get("pe_ratio"),
                            "price_to_book": peer_profile["valuation"].get("price_to_book"),
                            "roe_pct": peer_profile["profitability"].get("return_on_equity_pct"),
                            "debt_to_equity": peer_profile["leverage"].get("debt_to_equity"),
                            "market_cap": peer_profile["valuation"].get("market_cap"),
                        }
                    )
                except DataSourceError:
                    continue
            if peer_rows:
                payload["peers"] = peer_rows
        except DataSourceError:
            pass

    return render(payload, response_format, f"{resolved.symbol} valuation")


@mcp.tool(name="trademcp_get_financial_statements", annotations=tool_annotations("Financial statements"))
async def trademcp_get_financial_statements(
    symbol: Annotated[str, _fmt_field("NSE symbol or company name, e.g. 'SBIN'")],
    period: Annotated[str, _fmt_field("'annual' or 'quarterly'")] = "annual",
    years: Annotated[int, _fmt_field("How many periods to include (1-10)")] = 5,
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Get income statement, balance sheet and cash flow line items for a stock.

    Shows revenue, gross profit, operating income, EBITDA, net income and EPS
    from the income statement; total assets, debt, equity and working capital
    from the balance sheet; and operating cash flow, free cash flow and capex
    from the cash flow statement, across the requested number of periods.

    Args:
        symbol: NSE symbol or company name
        period: 'annual' or 'quarterly'
        years: number of periods to include
        response_format: 'markdown' or 'json'

    Returns:
        Markdown or JSON with 'income_statement', 'balance_sheet' and 'cash_flow'.
    """
    try:
        resolved = await resolve(symbol)
    except (SymbolNotFound, DataSourceError) as exc:
        return error_text(exc)

    types = yahoo.ANNUAL_TYPES + yahoo.QUARTERLY_TYPES
    try:
        series = await yahoo.get_timeseries(resolved.yahoo_ticker, types, years=10)
    except DataSourceError as exc:
        return error_text(exc)

    statements = fa.build_statements(series, years=min(years, 10), quarters=period.lower() == "quarterly")
    payload = {"symbol": resolved.symbol, "name": resolved.name, **statements}
    return render(payload, response_format, f"{resolved.symbol} financial statements ({period})")
