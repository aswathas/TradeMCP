"""Fundamental analysis: ratios, growth, statements and a health score.

Yahoo supplies the raw statement lines; every ratio below is computed here so
the numbers are consistent and auditable rather than scraped from a screen.
"""

from __future__ import annotations

from typing import Any, Sequence

from ..formatting import Raw

Series = dict[str, list[dict[str, Any]]]


def series_of(data: Series, key: str) -> list[tuple[str, float]]:
    """One metric as an ascending (date, value) list."""
    points = data.get(key) or []
    rows = [(p["date"], float(p["value"])) for p in points if p.get("date") and p.get("value") is not None]
    return sorted(rows, key=lambda pair: pair[0])


def latest(data: Series, key: str) -> float | None:
    rows = series_of(data, key)
    return rows[-1][1] if rows else None


def latest_date(data: Series, key: str) -> str | None:
    rows = series_of(data, key)
    return rows[-1][0] if rows else None


def _safe_div(numerator: float | None, denominator: float | None, scale: float = 1.0) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * scale


def _growth(rows: Sequence[tuple[str, float]], years: int = 1) -> float | None:
    """Percentage growth over the last ``years`` observations."""
    if len(rows) < years + 1:
        return None
    old = rows[-(years + 1)][1]
    new = rows[-1][1]
    if old == 0:
        return None
    return (new - old) / abs(old) * 100


def _cagr(rows: Sequence[tuple[str, float]], years: int) -> float | None:
    """Compound annual growth rate over ``years`` observations."""
    if len(rows) < years + 1:
        return None
    first, last = rows[-(years + 1)][1], rows[-1][1]
    if first <= 0 or last <= 0:
        return None
    return ((last / first) ** (1 / years) - 1) * 100


def build_fundamentals(
    data: Series,
    *,
    price: float | None = None,
    screener: dict[str, Any] | None = None,
    symbol: str = "",
) -> dict[str, Any]:
    """Assemble the full fundamental picture for one symbol.

    Args:
        data: Yahoo fundamentals time series keyed by metric type
        price: latest share price, used for per-share and yield maths
        screener: optional Screener.in profile for India-specific ratios
        symbol: the NSE symbol, for labelling
    """
    revenue = latest(data, "annualTotalRevenue") or latest(data, "trailingTotalRevenue")
    gross_profit = latest(data, "annualGrossProfit")
    total_expenses = latest(data, "annualTotalExpenses")
    operating_income = latest(data, "annualOperatingIncome")
    ebitda = latest(data, "annualEBITDA")
    net_income = latest(data, "annualNetIncome")
    assets = latest(data, "annualTotalAssets")
    equity = latest(data, "annualStockholdersEquity")
    debt = latest(data, "annualTotalDebt")
    invested_capital = latest(data, "annualInvestedCapital")
    working_capital = latest(data, "annualWorkingCapital")
    cfo = latest(data, "annualOperatingCashFlow")
    capex = latest(data, "annualCapitalExpenditure")
    fcf = latest(data, "annualFreeCashFlow")
    interest = latest(data, "annualInterestExpense")
    pretax = latest(data, "annualPretaxIncome")
    eps = latest(data, "annualDilutedEPS")
    dps = latest(data, "annualDividendPerShare")
    shares = latest(data, "trailingSharesOutstanding") or latest(data, "annualDilutedAverageShares")
    cash = latest(data, "annualCashAndCashEquivalents")
    current_assets = latest(data, "annualCurrentAssets")
    current_liabilities = latest(data, "annualCurrentLiabilities")
    inventory = latest(data, "annualInventory")

    market_cap = latest(data, "trailingMarketCap")
    enterprise_value = latest(data, "trailingEnterprisesValue")
    pe = latest(data, "trailingPeRatio")
    ev_ebitda = latest(data, "trailingEnterprisesValueEBITDARatio")

    if market_cap is None and price and shares:
        market_cap = price * shares
    if enterprise_value is None and market_cap is not None and debt is not None:
        enterprise_value = market_cap + debt

    revenue_rows = series_of(data, "annualTotalRevenue")
    profit_rows = series_of(data, "annualNetIncome")
    eps_rows = series_of(data, "annualDilutedEPS")
    cfo_rows = series_of(data, "annualOperatingCashFlow")

    valuation: dict[str, Any] = {
        "market_cap": market_cap,
        "enterprise_value": enterprise_value,
        "pe_ratio": pe,
        "peg_ratio": latest(data, "trailingPegRatio"),
        "price_to_book": _safe_div(market_cap, equity),
        "price_to_sales": _safe_div(market_cap, revenue),
        "ev_to_ebitda": ev_ebitda or _safe_div(enterprise_value, ebitda),
        "ev_to_sales": _safe_div(enterprise_value, revenue),
        "dividend_yield_pct": latest(data, "trailingDividendYield"),
        "book_value_per_share": _safe_div(equity, shares),
        "eps_ttm": latest(data, "trailingEps") or eps,
        "dividend_per_share": dps,
    }
    if valuation["pe_ratio"] is None and price and eps:
        valuation["pe_ratio"] = _safe_div(price, eps)
    if valuation["dividend_yield_pct"] is None and price and dps:
        valuation["dividend_yield_pct"] = _safe_div(dps, price, 100)
    if valuation["peg_ratio"] is None:
        growth = _growth(revenue_rows, 3)
        if growth and growth > 0 and valuation["pe_ratio"]:
            valuation["peg_ratio"] = valuation["pe_ratio"] / growth

    # EBIT: preferred for ROCE/ROIC (the Indian convention), then EBIT, then EBITDA.
    ebit = None
    if pretax is not None and interest is not None:
        ebit = pretax + interest
    ebit = ebit or operating_income or ebitda

    profitability: dict[str, Any] = {
        "gross_margin_pct": _safe_div(gross_profit, revenue, 100),
        "operating_margin_pct": _safe_div(operating_income or ebit, revenue, 100),
        "ebitda_margin_pct": _safe_div(ebitda, revenue, 100),
        "net_margin_pct": _safe_div(net_income, revenue, 100),
        "return_on_equity_pct": _safe_div(net_income, equity, 100),
        "return_on_assets_pct": _safe_div(net_income, assets, 100),
        "roce_pct": _safe_div(ebit, invested_capital, 100),
        "roic_pct": _safe_div(ebit, (equity or 0) + (debt or 0), 100),
        "asset_turnover": _safe_div(revenue, assets),
        "equity_multiplier": _safe_div(assets, equity),
        "effective_tax_rate_pct": _safe_div((pretax or 0) - (net_income or 0), pretax, 100)
        if pretax
        else None,
    }

    leverage: dict[str, Any] = {
        "debt_to_equity": _safe_div(debt, equity),
        "debt_to_assets": _safe_div(debt, assets, 100),
        "cash_and_equivalents": cash,
        "net_debt": (debt - cash) if (debt is not None and cash is not None) else None,
        "net_debt_to_ebitda": _safe_div((debt - cash) if (debt is not None and cash is not None) else None, ebitda),
        "interest_coverage": _safe_div(operating_income or ebitda, interest),
        "debt_to_capital_pct": _safe_div(debt, (debt or 0) + (equity or 0), 100),
    }

    current_ratio = _safe_div(current_assets, current_liabilities) or latest(data, "trailingCurrentRatio")
    quick_ratio = (
        _safe_div((current_assets - inventory), current_liabilities)
        if (current_assets is not None and inventory is not None)
        else latest(data, "trailingQuickRatio")
    )
    liquidity: dict[str, Any] = {
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "cash_ratio": _safe_div(cash, current_liabilities),
        "working_capital": working_capital,
        "working_capital_per_share": _safe_div(working_capital, shares),
        "operating_cash_flow": cfo,
        "free_cash_flow": fcf,
        "fcf_margin_pct": _safe_div(fcf, revenue, 100),
        "cfo_to_net_income": _safe_div(cfo, net_income),
        "capex": capex,
        "cash_flow_per_share": _safe_div(cfo, shares),
        "fcf_per_share": _safe_div(fcf, shares),
    }

    growth: dict[str, Any] = {
        "revenue_yoy_pct": _growth(revenue_rows, 1),
        "net_income_yoy_pct": _growth(profit_rows, 1),
        "eps_yoy_pct": _growth(eps_rows, 1),
        "operating_cash_flow_yoy_pct": _growth(cfo_rows, 1),
        "revenue_cagr_3y_pct": _cagr(revenue_rows, 3),
        "revenue_cagr_5y_pct": _cagr(revenue_rows, 5),
        "net_income_cagr_3y_pct": _cagr(profit_rows, 3),
        "net_income_cagr_5y_pct": _cagr(profit_rows, 5),
    }

    dupont: dict[str, Any] = {
        "net_margin_pct": profitability["net_margin_pct"],
        "asset_turnover": profitability["asset_turnover"],
        "equity_multiplier": profitability["equity_multiplier"],
        "roe_from_dupont_pct": None,
    }
    if all(dupont[k] is not None for k in ("net_margin_pct", "asset_turnover", "equity_multiplier")):
        dupont["roe_from_dupont_pct"] = (
            dupont["net_margin_pct"] * dupont["asset_turnover"] * dupont["equity_multiplier"]
        )

    india: dict[str, Any] = {}
    if screener:
        top = screener.get("top_ratios") or {}
        rows = ((screener.get("ratios") or {}).get("rows") or {})
        periods = (screener.get("ratios") or {}).get("periods") or []
        latest_period = periods[-1] if periods else None
        market_cap_crore = top.get("Market Cap")
        india = {
            "roce_pct": top.get("ROCE"),
            "roe_pct": top.get("ROE"),
            "book_value": top.get("Book Value"),
            "face_value": top.get("Face Value"),
            "market_cap_crore": Raw(market_cap_crore) if market_cap_crore is not None else None,
            "debt_to_equity": (rows.get("Debt to equity") or [None])[-1],
            "roce_history": {p: v for p, v in zip(periods, rows.get("ROCE %") or rows.get("ROCE") or [])},
            "roce_period": latest_period,
            "debtor_days": (rows.get("Debtor Days") or [None])[-1],
            "inventory_days": (rows.get("Inventory Days") or [None])[-1],
            "days_payable": (rows.get("Days Payable") or [None])[-1],
            "cash_conversion_cycle": (rows.get("Cash Conversion Cycle") or [None])[-1],
            "shareholding": screener.get("shareholding") or {},
        }
        if valuation.get("dividend_yield_pct") is None and top.get("Dividend Yield") is not None:
            valuation["dividend_yield_pct"] = top["Dividend Yield"]
        if profitability.get("roce_pct") is None and india.get("roce_pct") is not None:
            profitability["roce_pct"] = india["roce_pct"]
        if profitability.get("return_on_equity_pct") is None and india.get("roe_pct") is not None:
            profitability["return_on_equity_pct"] = india["roe_pct"]

    health = health_score(valuation, profitability, leverage, liquidity, growth)

    return {
        "symbol": symbol,
        "as_of": {
            "annual": latest_date(data, "annualTotalRevenue"),
            "trailing": latest_date(data, "trailingMarketCap"),
            "price": price,
        },
        "valuation": valuation,
        "profitability": profitability,
        "leverage": leverage,
        "liquidity": liquidity,
        "growth": growth,
        "dupont": dupont,
        "india_specific": india,
        "health_score": health,
        "raw_series": {
            "revenue": revenue_rows[-5:],
            "net_income": profit_rows[-5:],
            "eps": eps_rows[-5:],
        },
    }


def health_score(
    valuation: dict[str, Any],
    profitability: dict[str, Any],
    leverage: dict[str, Any],
    liquidity: dict[str, Any],
    growth: dict[str, Any],
) -> dict[str, Any]:
    """A 0-100 composite health score with the component breakdown."""
    checks: list[tuple[str, float, float, float]] = [
        # (name, value, good_threshold, weight)
        ("return_on_equity_pct", profitability.get("return_on_equity_pct"), 15.0, 15),
        ("roce_pct", profitability.get("roce_pct"), 15.0, 15),
        ("net_margin_pct", profitability.get("net_margin_pct"), 10.0, 10),
        ("operating_margin_pct", profitability.get("operating_margin_pct"), 10.0, 8),
        ("debt_to_equity", leverage.get("debt_to_equity"), 0.5, 12),
        ("interest_coverage", leverage.get("interest_coverage"), 4.0, 8),
        ("current_ratio", liquidity.get("current_ratio"), 1.5, 8),
        ("revenue_cagr_3y_pct", growth.get("revenue_cagr_3y_pct"), 8.0, 12),
        ("net_income_cagr_3y_pct", growth.get("net_income_cagr_3y_pct"), 8.0, 7),
        ("fcf_margin_pct", liquidity.get("fcf_margin_pct"), 5.0, 5),
    ]

    earned = 0.0
    total = 0.0
    details: list[dict[str, Any]] = []
    for name, value, good, weight in checks:
        total += weight
        if value is None:
            details.append({"metric": name, "value": None, "score": 0, "weight": weight, "note": "no data"})
            continue
        if name == "debt_to_equity":
            score = weight if value <= good / 2 else (weight * 0.6 if value <= good else (weight * 0.25 if value <= 1.5 else 0))
        elif name in ("current_ratio", "interest_coverage"):
            score = weight if value >= good else (weight * 0.6 if value >= 1 else weight * 0.3)
        else:
            score = weight if value >= good else (weight * (value / good) if good else 0)
        earned += score
        details.append({"metric": name, "value": round(value, 2), "score": round(score, 2), "weight": weight})

    score = round(100 * earned / total, 1) if total else 0.0
    if score >= 75:
        label = "Strong"
    elif score >= 55:
        label = "Healthy"
    elif score >= 35:
        label = "Mixed"
    else:
        label = "Weak"

    return {"score": score, "label": label, "components": details}


def build_statements(data: Series, *, years: int = 5, quarters: bool = False) -> dict[str, Any]:
    """Income statement, balance sheet and cash flow as reported line items."""
    prefix = "quarterly" if quarters else "annual"

    def block(mapping: dict[str, str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for label, key in mapping.items():
            rows = series_of(data, f"{prefix}{key}")
            if rows:
                out[label] = {date: value for date, value in rows[-years:]}
        return out

    income = block(
        {
            "revenue": "TotalRevenue",
            "gross_profit": "GrossProfit",
            "operating_income": "OperatingIncome",
            "ebitda": "EBITDA",
            "net_income": "NetIncome",
            "eps_diluted": "DilutedEPS",
        }
    )
    balance = block(
        {
            "total_assets": "TotalAssets",
            "total_debt": "TotalDebt",
            "shareholders_equity": "StockholdersEquity",
            "working_capital": "WorkingCapital",
            "invested_capital": "InvestedCapital",
        }
    )
    cash_flow = block(
        {
            "operating_cash_flow": "OperatingCashFlow",
            "free_cash_flow": "FreeCashFlow",
            "capital_expenditure": "CapitalExpenditure",
        }
    )
    periods = sorted({d for block_ in (income, balance, cash_flow) for row in block_.values() for d in row})
    return {
        "period_type": "quarterly" if quarters else "annual",
        "periods": periods,
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow": cash_flow,
    }
