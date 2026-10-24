"""Resolve user input (name, NSE code, ticker, ISIN) into tradable identifiers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .providers import nse, yahoo

# Yahoo tickers for the indices Indian traders watch.
INDEX_TICKERS: dict[str, str] = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "BANKNIFTY": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY MEDIA": "^CNXMEDIA",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY PSU BANK": "^CNXPSUBANK",
    "NIFTY PRIVATE BANK": "^NIFTYPVTBANK",
    "NIFTY FINANCIAL SERVICES": "^CNXFIN",
    "NIFTY 500": "^CNX500",
    "NIFTY TOTAL MARKET": "^CNXTMC",
    "SENSEX": "^BSESN",
    "INDIA VIX": "^INDIAVIX",
}

_INDEX_ALIASES = {
    "NIFTY": "NIFTY 50",
    "NIFTY50": "NIFTY 50",
    "NIFTY50": "NIFTY 50",
    "SENSEX": "SENSEX",
    "BSE SENSEX": "SENSEX",
    "VIX": "INDIA VIX",
    "INDIAVIX": "INDIA VIX",
    "BANKNIFTY": "NIFTY BANK",
    "BANK NIFTY": "NIFTY BANK",
}

_NOISE = re.compile(
    r"\b(limited|ltd\.?|plc|inc\.?|corporation|corp\.?|company|co\.?|industries|india|"
    r"enterprises)\b"
)


@dataclass(slots=True)
class ResolvedSymbol:
    """Everything needed to fetch data for one instrument."""

    query: str
    symbol: str
    name: str
    yahoo_ticker: str
    exchange: str = "NSE"
    isin: str = ""
    industry: str = ""
    is_index: bool = False
    alternatives: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "symbol": self.symbol,
            "name": self.name,
            "yahoo_ticker": self.yahoo_ticker,
            "exchange": self.exchange,
            "isin": self.isin,
            "industry": self.industry,
            "is_index": self.is_index,
            "alternatives": self.alternatives,
        }


class SymbolNotFound(LookupError):
    """The user input did not match any known Indian instrument."""


def _norm(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = _NOISE.sub(" ", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _name_score(query: str, name: str) -> float:
    """0.0 - 1.0 similarity between a query and a company name."""
    q, n = _norm(query), _norm(name)
    if not q or not n:
        return 0.0
    if q == n:
        return 1.0
    q_tokens, n_tokens = set(q.split()), set(n.split())
    if not q_tokens or not n_tokens:
        return 0.0
    if q_tokens <= n_tokens:
        return 0.95
    if n_tokens <= q_tokens:
        return 0.9
    overlap = len(q_tokens & n_tokens) / len(q_tokens)
    return round(overlap * 0.8, 3)


async def resolve(query: str, exchange: str = "NSE") -> ResolvedSymbol:
    """Resolve a symbol, company name, ISIN or Yahoo ticker.

    Args:
        query: e.g. "RELIANCE", "reliance industries", "NSE:TCS", "RELIANCE.NS", "INE002A01018"
        exchange: preferred listing, "NSE" or "BSE"

    Raises:
        SymbolNotFound: nothing matched
    """
    raw = (query or "").strip()
    if not raw:
        raise SymbolNotFound("Empty symbol. Pass an NSE code like 'RELIANCE' or a company name.")

    cleaned = raw.upper().replace(" ", "")

    # 1. Index alias
    alias = _INDEX_ALIASES.get(cleaned) or _INDEX_ALIASES.get(raw.upper())
    if alias:
        return ResolvedSymbol(
            query=raw,
            symbol=alias,
            name=alias,
            yahoo_ticker=INDEX_TICKERS[alias],
            exchange="INDEX",
            is_index=True,
        )

    # 2. Already a Yahoo ticker
    if re.search(r"\.(NS|BO)$", raw.upper()):
        ticker = raw.upper()
        base = ticker.split(".")[0]
        return await _enrich(raw, base, ticker, "NSE" if ticker.endswith(".NS") else "BSE")

    # 3. NSE-prefixed form (NSE:RELIANCE)
    if ":" in raw:
        prefix, _, rest = raw.partition(":")
        if prefix.upper() in ("NSE", "BSE") and rest:
            rest = rest.strip().upper()
            if rest.endswith(".NS") or rest.endswith(".BO"):
                return await resolve(rest, exchange)
            ticker = f"{rest}.NS" if prefix.upper() == "NSE" else f"{rest}.BO"
            return await _enrich(raw, rest, ticker, prefix.upper())

    # 4. Exact NSE symbol
    master = await nse.get_equity_master()
    if raw.upper() in master:
        row = master[raw.upper()]
        return ResolvedSymbol(
            query=raw,
            symbol=row["symbol"],
            name=row["name"],
            yahoo_ticker=f"{row['symbol']}.NS",
            exchange="NSE",
            isin=row.get("isin", ""),
            industry=await _industry_for(row["symbol"]),
        )

    # 5. ISIN
    for row in master.values():
        if row.get("isin") and row["isin"].upper() == cleaned:
            return ResolvedSymbol(
                query=raw,
                symbol=row["symbol"],
                name=row["name"],
                yahoo_ticker=f"{row['symbol']}.NS",
                exchange="NSE",
                isin=row["isin"],
                industry=await _industry_for(row["symbol"]),
            )

    # 6. Company-name match against NSE listings
    best = _best_name_match(raw, master.values())
    if best:
        return ResolvedSymbol(
            query=raw,
            symbol=best["symbol"],
            name=best["name"],
            yahoo_ticker=f"{best['symbol']}.NS",
            exchange="NSE",
            isin=best.get("isin", ""),
            industry=await _industry_for(best["symbol"]),
        )

    # 7. Yahoo search fallback
    matches = await yahoo.search(raw, count=8)
    indian = [
        m
        for m in matches
        if m.get("symbol")
        and (
            str(m["symbol"]).endswith(".NS")
            or str(m["symbol"]).endswith(".BO")
            or str(m.get("exchange", "")).upper() in ("NSE", "BSE", "BOM")
        )
    ]
    pool = indian or matches
    if pool:
        top = pool[0]
        ticker = top["symbol"]
        base = ticker.split(".")[0]
        return ResolvedSymbol(
            query=raw,
            symbol=base,
            name=top.get("name") or base,
            yahoo_ticker=ticker,
            exchange="NSE" if ticker.endswith(".NS") else ("BSE" if ticker.endswith(".BO") else "NSE"),
            alternatives=[{"symbol": m["symbol"], "name": m.get("name"), "exchange": m.get("exchange")} for m in pool[1:6]],
        )

    raise SymbolNotFound(
        f"No Indian instrument matched '{raw}'. Use trademcp_search_symbol to explore, or pass an "
        "NSE code such as 'RELIANCE'."
    )


async def _enrich(query: str, symbol: str, ticker: str, exchange: str) -> ResolvedSymbol:
    """Fill in company name / ISIN / industry for a symbol we already know."""
    master = await nse.get_equity_master()
    row = master.get(symbol.upper())
    return ResolvedSymbol(
        query=query,
        symbol=symbol.upper(),
        name=(row or {}).get("name", symbol.upper()),
        yahoo_ticker=ticker,
        exchange=exchange,
        isin=(row or {}).get("isin", ""),
        industry=await _industry_for(symbol.upper()),
    )


async def _industry_for(symbol: str) -> str:
    """Industry from the NIFTY 500 list; empty for stocks outside the index."""
    try:
        for row in await nse.get_index_constituents("NIFTY 500"):
            if row["symbol"] == symbol:
                return row.get("industry", "")
    except Exception:
        return ""
    return ""


def _best_name_match(query: str, rows) -> dict[str, Any] | None:
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        score = _name_score(query, row.get("name", ""))
        if score >= 0.8:
            scored.append((score, row))
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]


async def search_symbols(query: str, limit: int = 15) -> list[dict[str, Any]]:
    """Search NSE listings by symbol or company name."""
    master = await nse.get_equity_master()
    q = query.strip().upper()
    results: list[dict[str, Any]] = []

    if q:
        for row in master.values():
            if row["symbol"].startswith(q):
                results.append({**row, "match": "symbol"})
        for row in master.values():
            score = _name_score(query, row.get("name", ""))
            if score >= 0.8:
                results.append({**row, "match": "name", "score": score})

    if not results:
        for match in await yahoo.search(query, count=limit):
            base = str(match.get("symbol", "")).split(".")[0]
            row = master.get(base)
            results.append(
                {
                    "symbol": base,
                    "name": match.get("name"),
                    "exchange": match.get("exchange"),
                    "isin": (row or {}).get("isin", ""),
                    "match": "yahoo",
                }
            )

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in results:
        if row["symbol"] in seen:
            continue
        seen.add(row["symbol"])
        unique.append(row)
    return unique[:limit]
