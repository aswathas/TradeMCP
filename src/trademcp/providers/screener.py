"""Screener.in provider - India-specific fundamentals.

Adds the ratios Indian investors actually use (ROCE, ROE, promoter holding,
FII/DII flows, working-capital days) on top of what the statement APIs give us.
Parsing is intentionally defensive: if the markup shifts we degrade to fewer
fields instead of failing the whole tool call.
"""

from __future__ import annotations

import html as html_lib
import re
from typing import Any

from .. import config
from ..cache import cache
from ..http import DataSourceError, get_text

_BASE = "https://www.screener.in/company/{symbol}/consolidated/"


def _text(raw: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()


def _label(raw: str) -> str:
    """Row/field label with entities resolved (screener.in uses &nbsp; heavily)."""
    return _text(html_lib.unescape(raw)).replace("\xa0", " ").strip()


def _number(raw: str) -> float | None:
    cleaned = _text(raw).replace(",", "").replace("₹", "").replace("%", "").strip()
    if cleaned in ("", "-", "None", "NA"):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _section(html: str, section_id: str) -> str:
    match = re.search(r'<section[^>]*id="%s"[^>]*>(.*?)</section>' % re.escape(section_id), html, re.S)
    return match.group(1) if match else ""


def _parse_top_ratios(html: str) -> dict[str, Any]:
    """The <ul id="top-ratios"> summary block.

    Values are floats; 'High / Low' carries two numbers so it becomes a list.
    """
    block = re.search(r'<ul id="top-ratios">(.*?)</ul>', html, re.S)
    if not block:
        return {}

    out: dict[str, Any] = {}
    for item in re.findall(r"<li[^>]*>(.*?)</li>", block.group(1), re.S):
        name_match = re.search(r'<span class="name">(.*?)</span>', item, re.S)
        if not name_match:
            continue
        name = _label(name_match.group(1))
        numbers = [_number(n) for n in re.findall(r'<span class="number">(.*?)</span>', item, re.S)]
        numbers = [n for n in numbers if n is not None]
        if not numbers:
            continue
        out[name] = numbers[0] if len(numbers) == 1 else numbers
    return out


def _parse_table(section_html: str) -> tuple[list[str], dict[str, list[float | None]]]:
    """Parse the first table of a section into (periods, {row_name: [values]})."""
    table = re.search(r"<table.*?</table>", section_html, re.S)
    if not table:
        return [], {}

    headers = [_label(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table.group(0), re.S)]
    periods = headers[1:]

    rows: dict[str, list[float | None]] = {}
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", table.group(0), re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)
        if not cells:
            continue
        name = _label(cells[0])
        if not name:
            continue
        rows[name] = [_number(cell) for cell in cells[1:]]
    return periods, rows


def _parse_shareholding(html: str) -> dict[str, Any]:
    """Latest promoter / FII / DII / public holding percentages."""
    section = _section(html, "shareholding")
    tables = re.findall(r"<table.*?</table>", section, re.S)
    if not tables:
        return {}

    table = tables[0]
    headers = [_label(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S)]
    periods = headers[1:]
    out: dict[str, Any] = {"periods": periods}

    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)
        if len(cells) < 2:
            continue
        name = _label(cells[0])
        values = [_number(cell) for cell in cells[1:]]
        if name:
            out[name] = values
    return out


async def get_company_profile(symbol: str, *, use_cache: bool = True) -> dict[str, Any]:
    """Screener.in profile for an NSE symbol: top ratios, ratio history, holding pattern."""
    cache_key = f"screener:{symbol.upper()}"
    if use_cache:
        cached = await cache.get(cache_key, config.PROFILE_TTL)
        if cached:
            return cached

    html = await get_text(_BASE.format(symbol=symbol.upper()), source=f"Screener.in ({symbol})")

    top = _parse_top_ratios(html)
    periods, ratios = _parse_table(_section(html, "ratios"))
    pl_periods, pl_rows = _parse_table(_section(html, "profit-loss"))
    cf_periods, cf_rows = _parse_table(_section(html, "cash-flow"))
    bs_periods, bs_rows = _parse_table(_section(html, "balance-sheet"))
    holding = _parse_shareholding(html)

    result: dict[str, Any] = {
        "source": "screener.in",
        "symbol": symbol.upper(),
        "top_ratios": top,
        "ratios": {"periods": periods, "rows": ratios},
        "profit_loss": {"periods": pl_periods, "rows": pl_rows},
        "cash_flow": {"periods": cf_periods, "rows": cf_rows},
        "balance_sheet": {"periods": bs_periods, "rows": bs_rows},
        "shareholding": holding,
    }

    if use_cache:
        await cache.set(cache_key, result)
    return result


async def safe_company_profile(symbol: str) -> dict[str, Any] | None:
    """Profile lookup that never raises - callers treat this source as optional."""
    if not config.ENABLE_SCREENER_IN:
        return None
    try:
        return await get_company_profile(symbol)
    except (DataSourceError, Exception):
        return None
