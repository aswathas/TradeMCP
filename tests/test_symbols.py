"""Unit tests for symbol normalisation and the tool surface - no network."""

from __future__ import annotations

import pytest

from trademcp import symbols
from trademcp.formatting import Raw, fmt_number, to_markdown


class TestNameMatching:
    def test_suffixes_are_ignored(self):
        assert symbols._name_score("Reliance Industries", "Reliance Industries Limited") > 0.9

    def test_exact_match_scores_one(self):
        assert symbols._name_score("TCS", "TCS") == 1.0

    def test_extra_tokens_are_a_subset_match(self):
        assert symbols._name_score("tata motors", "Tata Motors Limited") > 0.9

    def test_unrelated_names_score_low(self):
        assert symbols._name_score("reliance", "Infosys Limited") < 0.8

    def test_empty_query_scores_zero(self):
        assert symbols._name_score("", "Infosys Limited") == 0.0


class TestIndexAliases:
    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("nifty", "NIFTY 50"),
            ("NIFTY", "NIFTY 50"),
            ("banknifty", "NIFTY BANK"),
            ("sensex", "SENSEX"),
            ("vix", "INDIA VIX"),
        ],
    )
    def test_aliases_map_to_indices(self, alias, expected):
        assert symbols._INDEX_ALIASES[alias.upper().replace(" ", "")] == expected

    def test_every_index_has_a_ticker(self):
        for name in symbols.INDEX_TICKERS.values():
            assert name.startswith("^")


class TestFormatting:
    def test_large_numbers_use_indian_units(self):
        assert "Cr" in fmt_number(1_688_852_584_7232.0)
        assert "L" in fmt_number(250_000.0)

    def test_small_numbers_use_plain_format(self):
        assert fmt_number(1234.5) == "1,234.50"

    def test_none_renders_as_dash(self):
        assert fmt_number(None) == "-"

    def test_raw_bypasses_unit_scaling(self):
        assert fmt_number(Raw(1_626_611.0)) == "1,626,611.00"

    def test_markdown_renders_nested_dicts(self):
        text = to_markdown({"valuation": {"pe_ratio": 22.5}}, "Test")
        assert "# Test" in text
        assert "Pe Ratio" in text
        assert "22.50" in text

    def test_markdown_renders_lists_of_dicts_as_a_table(self):
        text = to_markdown({"rows": [{"a": 1, "b": 2}]}, "Test")
        assert "| A" in text and "| B" in text


class TestToolSurface:
    def test_every_tool_is_registered(self):
        import asyncio

        from trademcp import tools  # noqa: F401
        from trademcp.app import mcp

        registered = asyncio.run(mcp.list_tools())
        names = {t.name for t in registered}
        expected = {
            "trademcp_search_symbol",
            "trademcp_get_quote",
            "trademcp_get_price_history",
            "trademcp_get_index_snapshot",
            "trademcp_get_market_breadth",
            "trademcp_compare_stocks",
            "trademcp_get_technical_indicators",
            "trademcp_get_technical_analysis",
            "trademcp_get_support_resistance",
            "trademcp_get_fundamentals",
            "trademcp_get_valuation",
            "trademcp_get_financial_statements",
            "trademcp_screen_stocks",
            "trademcp_analyze_portfolio",
        }
        assert expected <= names

    def test_tools_are_annotated_read_only(self):
        import asyncio

        from trademcp import tools  # noqa: F401
        from trademcp.app import mcp

        for tool in asyncio.run(mcp.list_tools()):
            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False

    def test_tool_names_are_prefixed(self):
        import asyncio

        from trademcp import tools  # noqa: F401
        from trademcp.app import mcp

        for tool in asyncio.run(mcp.list_tools()):
            assert tool.name.startswith("trademcp_")
