"""Offline tests for the tool layer - no network, provider calls are stubbed."""

from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

from trademcp import symbols
from trademcp.http import DataSourceError
from trademcp.providers import yahoo
from trademcp.providers.yahoo import Bar
from trademcp.symbols import ResolvedSymbol
from trademcp.tools import market, screener, technical
from trademcp.tools.common import ResponseFormat


def _bars(closes: list[float]) -> list[Bar]:
    return [
        Bar(date=f"d{i}", open=c, high=c, low=c, close=c, volume=100)
        for i, c in enumerate(closes)
    ]


def _resolved(symbol: str = "RELIANCE") -> ResolvedSymbol:
    return ResolvedSymbol(
        query=symbol,
        symbol=symbol,
        name="Reliance Industries Limited",
        yahoo_ticker=f"{symbol}.NS",
    )


class TestIndexSnapshotDefaults:
    def test_default_set_has_fifteen_indices(self):
        assert len(market.DEFAULT_INDICES) == 15

    def test_every_default_index_resolves_to_a_ticker(self):
        for name in market.DEFAULT_INDICES:
            assert name in symbols.INDEX_TICKERS, name

    def test_default_set_has_no_duplicates(self):
        assert len(set(market.DEFAULT_INDICES)) == len(market.DEFAULT_INDICES)

    def test_default_set_covers_the_promised_sector_indices(self):
        # The docstring promises these twelve sector indices plus NIFTY 50,
        # SENSEX and INDIA VIX.
        promised = [
            "NIFTY BANK", "NIFTY IT", "NIFTY AUTO", "NIFTY FMCG", "NIFTY PHARMA",
            "NIFTY REALTY", "NIFTY METAL", "NIFTY ENERGY", "NIFTY PSU BANK",
            "NIFTY PRIVATE BANK", "NIFTY FINANCIAL SERVICES", "NIFTY MEDIA",
        ]
        for name in promised:
            assert name in market.DEFAULT_INDICES, name
        assert "NIFTY 50" in market.DEFAULT_INDICES
        assert "SENSEX" in market.DEFAULT_INDICES
        assert "INDIA VIX" in market.DEFAULT_INDICES

    def test_tool_fetches_the_whole_default_set(self, monkeypatch):
        async def fake_get_quotes(tickers):
            return {
                t: {
                    "regularMarketPrice": 100.0,
                    "regularMarketChange": 1.0,
                    "regularMarketChangePercent": 1.0,
                }
                for t in tickers
            }

        monkeypatch.setattr(yahoo, "get_quotes", fake_get_quotes)
        out = asyncio.run(market.trademcp_get_index_snapshot(response_format=ResponseFormat.JSON))
        payload = json.loads(out)
        assert payload["index_count"] == 15
        assert "unavailable" not in payload


class TestTechnicalRegistry:
    def test_registry_has_57_indicators(self):
        assert len(technical.REGISTRY) == 57

    def test_registry_names_are_unique(self):
        assert len(set(technical.REGISTRY)) == 57

    def test_agent_facing_text_says_57_not_60_plus(self, monkeypatch):
        from trademcp import tools  # noqa: F401
        from trademcp.app import mcp

        registered = {t.name: t for t in asyncio.run(mcp.list_tools())}
        description = registered["trademcp_get_technical_indicators"].description or ""
        assert "60+" not in description
        assert "57" in description
        indicators_desc = registered["trademcp_get_technical_indicators"].input_schema[
            "properties"
        ]["indicators"]["description"]
        assert "60+" not in indicators_desc
        assert "57" in indicators_desc

    def test_server_instructions_say_57(self):
        from trademcp import tools  # noqa: F401
        from trademcp.app import mcp

        assert "40+" not in (mcp.instructions or "")
        assert "57 technical indicators" in (mcp.instructions or "")


class TestQuoteReturns:
    def test_window_return_uses_the_window_endpoints(self):
        closes = [100.0, 105.0, 110.0]
        assert market.window_return(closes) == pytest.approx(10.0)

    def test_window_return_needs_two_closes(self):
        assert market.window_return([100.0]) is None
        assert market.window_return([]) is None

    def test_period_return_of_a_short_window_is_none(self):
        # 248 daily bars is a full trading year, so a 252-bar lookback can
        # never be indexed - this is what made 1_year_pct always null.
        closes = [100.0 + i for i in range(248)]
        assert market.period_return(closes, 252) is None
        assert market.period_return(closes, 21) is not None

    def test_period_return_uses_the_indexed_close(self):
        closes = [100.0, 101.0, 102.0, 110.0]
        assert market.period_return(closes, 1) == pytest.approx((110.0 - 102.0) / 102.0 * 100)

    def test_quote_tool_reports_the_1_year_return(self, monkeypatch):
        closes = [100.0 + i * 0.1 for i in range(248)]

        async def fake_get_quotes(tickers):
            return {t: {"regularMarketPrice": closes[-1], "currency": "INR"} for t in tickers}

        async def fake_get_bars(symbol, *, range_="1y", interval="1d", **kwargs):
            return _bars(closes), {}

        async def fake_resolve(query, exchange="NSE"):
            return _resolved(query)

        monkeypatch.setattr(yahoo, "get_quotes", fake_get_quotes)
        monkeypatch.setattr(yahoo, "get_bars", fake_get_bars)
        monkeypatch.setattr(market, "resolve", fake_resolve)

        out = asyncio.run(
            market.trademcp_get_quote("RELIANCE", response_format=ResponseFormat.JSON)
        )
        payload = json.loads(out)
        returns = payload["returns"]
        expected = (closes[-1] - closes[0]) / closes[0] * 100
        assert returns["1_year_pct"] == pytest.approx(expected)
        assert returns["1_week_pct"] is not None
        assert returns["1_month_pct"] is not None
        assert returns["3_month_pct"] is not None
        assert returns["6_month_pct"] is not None


class TestFriendlyErrors:
    def test_quote_tool_turns_a_data_source_error_into_readable_text(self, monkeypatch):
        async def boom(tickers):
            raise DataSourceError(
                "Yahoo Finance quote: request failed after 3 attempts (ReadTimeout)."
            )

        async def fake_resolve(query, exchange="NSE"):
            return _resolved(query)

        monkeypatch.setattr(yahoo, "get_quotes", boom)
        monkeypatch.setattr(market, "resolve", fake_resolve)

        out = asyncio.run(
            market.trademcp_get_quote("RELIANCE", response_format=ResponseFormat.JSON)
        )
        assert out.startswith("Error: ")
        assert "ReadTimeout" in out


class TestCacheKey:
    def test_fundamentals_cache_key_is_deterministic(self):
        key = yahoo._timeseries_cache_key("RELIANCE.NS", ["annualTotalRevenue", "annualNetIncome"], 5)
        again = yahoo._timeseries_cache_key("RELIANCE.NS", ["annualTotalRevenue", "annualNetIncome"], 5)
        assert key == again
        assert key.startswith("ts:RELIANCE.NS:")
        assert key.endswith(":5")
        # The digest is a plain sha256 of the joined names, not a salted hash().
        digest = hashlib.sha256(b"annualNetIncome,annualTotalRevenue").hexdigest()[:16]
        assert digest in key
        # Order of the requested metrics does not change the key.
        shuffled = yahoo._timeseries_cache_key("RELIANCE.NS", ["annualNetIncome", "annualTotalRevenue"], 5)
        assert shuffled == key

    def test_fundamentals_cache_key_changes_with_the_request(self):
        base = yahoo._timeseries_cache_key("RELIANCE.NS", ["annualTotalRevenue"], 5)
        assert yahoo._timeseries_cache_key("TCS.NS", ["annualTotalRevenue"], 5) != base
        assert yahoo._timeseries_cache_key("RELIANCE.NS", ["annualTotalRevenue"], 6) != base
        assert yahoo._timeseries_cache_key("RELIANCE.NS", ["annualNetIncome"], 5) != base


def _profile(pe: float | None) -> dict:
    return {
        "valuation": {"pe_ratio": pe, "market_cap": 1_000_000_000.0, "price_to_book": 1.5},
        "profitability": {"return_on_equity_pct": 12.0, "roce_pct": 14.0, "net_margin_pct": 8.0},
        "leverage": {"debt_to_equity": 0.4},
        "liquidity": {"current_ratio": 1.8},
        "growth": {"revenue_cagr_3y_pct": 6.0},
        "health_score": {"score": 60.0, "label": "Healthy"},
    }


_PE_BY_SYMBOL = {"CHEAP": 10.0, "MID": 18.0, "RICH": 40.0, "LOSS": None}


def _stub_screener(monkeypatch, master: dict[str, dict], pes: dict[str, float | None]):
    async def fake_get_equity_master():
        return master

    async def fake_fetch_profiles(symbols_):
        return {s: _profile(pes.get(s)) for s in symbols_ if s in pes}

    async def fake_get_quotes(tickers):
        return {}

    monkeypatch.setattr(screener.nse, "get_equity_master", fake_get_equity_master)
    monkeypatch.setattr(screener, "_fetch_profiles", fake_fetch_profiles)
    monkeypatch.setattr(yahoo, "get_quotes", fake_get_quotes)


def _master(names: list[str]) -> dict[str, dict]:
    return {n: {"symbol": n, "name": f"{n} Ltd"} for n in names}


class TestScreenerPeBounds:
    def test_min_pe_is_a_floor(self):
        assert screener.pe_in_band(18.0, 15.0, None) is True
        assert screener.pe_in_band(10.0, 15.0, None) is False
        assert screener.pe_in_band(None, 15.0, None) is False

    def test_max_pe_is_a_ceiling(self):
        assert screener.pe_in_band(18.0, None, 20.0) is True
        assert screener.pe_in_band(40.0, None, 20.0) is False
        assert screener.pe_in_band(None, None, 20.0) is False

    def test_both_bounds_together(self):
        assert screener.pe_in_band(18.0, 15.0, 20.0) is True
        assert screener.pe_in_band(14.0, 15.0, 20.0) is False
        assert screener.pe_in_band(21.0, 15.0, 20.0) is False

    def test_no_bounds_accepts_everything(self):
        assert screener.pe_in_band(None, None, None) is True

    def test_screen_keeps_stocks_at_or_above_min_pe(self, monkeypatch):
        _stub_screener(monkeypatch, _master(list(_PE_BY_SYMBOL)), _PE_BY_SYMBOL)
        out = asyncio.run(
            screener.trademcp_screen_stocks(
                universe="NSE", min_pe=15.0, response_format=ResponseFormat.JSON
            )
        )
        payload = json.loads(out)
        symbols_out = {row["symbol"] for row in payload["matches"]}
        assert symbols_out == {"MID", "RICH"}

    def test_screen_keeps_stocks_at_or_below_max_pe(self, monkeypatch):
        _stub_screener(monkeypatch, _master(list(_PE_BY_SYMBOL)), _PE_BY_SYMBOL)
        out = asyncio.run(
            screener.trademcp_screen_stocks(
                universe="NSE", max_pe=20.0, response_format=ResponseFormat.JSON
            )
        )
        payload = json.loads(out)
        symbols_out = {row["symbol"] for row in payload["matches"]}
        assert symbols_out == {"CHEAP", "MID"}

    def test_tool_schema_documents_the_new_semantics(self):
        from trademcp import tools  # noqa: F401
        from trademcp.app import mcp

        registered = {t.name: t for t in asyncio.run(mcp.list_tools())}
        properties = registered["trademcp_screen_stocks"].input_schema["properties"]
        assert "at or above" in properties["min_pe"]["description"]
        assert "at or below" in properties["max_pe"]["description"]


class TestScreenerUniverseDisclosure:
    def test_small_universe_is_not_truncated(self, monkeypatch):
        _stub_screener(monkeypatch, _master(["MID"]), _PE_BY_SYMBOL)
        out = asyncio.run(
            screener.trademcp_screen_stocks(universe="NSE", response_format=ResponseFormat.JSON)
        )
        payload = json.loads(out)
        assert payload["universe_truncated"] is False
        assert payload["universe_size"] == 1
        assert payload["symbols_scanned"] == 1

    def test_large_universe_is_truncated_and_says_so(self, monkeypatch):
        names = [f"SYM{i:04d}" for i in range(700)]
        _stub_screener(monkeypatch, _master(names), _PE_BY_SYMBOL)
        out = asyncio.run(
            screener.trademcp_screen_stocks(universe="NSE", response_format=ResponseFormat.JSON)
        )
        payload = json.loads(out)
        assert payload["universe_size"] == 700
        assert payload["symbols_scanned"] == screener.MAX_UNIVERSE_SCAN
        assert payload["universe_truncated"] is True
        assert payload["universe_scan_cap"] == screener.MAX_UNIVERSE_SCAN

    def test_universe_description_does_not_promise_every_listed_stock(self):
        from trademcp import tools  # noqa: F401
        from trademcp.app import mcp

        registered = {t.name: t for t in asyncio.run(mcp.list_tools())}
        description = registered["trademcp_screen_stocks"].input_schema["properties"][
            "universe"
        ]["description"]
        assert "(all listed)" not in description
        assert "600" in description
