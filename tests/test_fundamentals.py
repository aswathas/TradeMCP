"""Unit tests for fundamental ratio derivation - no network."""

from __future__ import annotations

import pytest

from trademcp.analytics import fundamentals as fa


def series(name: str, values: list[tuple[str, float]]) -> dict[str, list[dict]]:
    return {
        name: [
            {"date": date, "period_type": "12M", "value": value, "currency": "INR"}
            for date, value in values
        ]
    }


@pytest.fixture
def simple_profile() -> dict:
    """Two years of clean numbers for a 100-crore-revenue company."""
    data: dict[str, list[dict]] = {}
    data.update(series("annualTotalRevenue", [("2024-03-31", 1000.0), ("2025-03-31", 1200.0)]))
    data.update(series("annualNetIncome", [("2024-03-31", 100.0), ("2025-03-31", 150.0)]))
    data.update(series("annualGrossProfit", [("2024-03-31", 400.0), ("2025-03-31", 480.0)]))
    data.update(series("annualEBITDA", [("2024-03-31", 200.0), ("2025-03-31", 240.0)]))
    data.update(series("annualTotalAssets", [("2024-03-31", 1000.0), ("2025-03-31", 1200.0)]))
    data.update(series("annualStockholdersEquity", [("2024-03-31", 500.0), ("2025-03-31", 600.0)]))
    data.update(series("annualTotalDebt", [("2024-03-31", 200.0), ("2025-03-31", 300.0)]))
    data.update(series("annualInvestedCapital", [("2024-03-31", 700.0), ("2025-03-31", 900.0)]))
    data.update(series("annualCashAndCashEquivalents", [("2024-03-31", 50.0), ("2025-03-31", 100.0)]))
    data.update(series("annualCurrentAssets", [("2024-03-31", 400.0), ("2025-03-31", 500.0)]))
    data.update(series("annualCurrentLiabilities", [("2024-03-31", 200.0), ("2025-03-31", 250.0)]))
    data.update(series("annualInventory", [("2024-03-31", 100.0), ("2025-03-31", 150.0)]))
    data.update(series("annualOperatingCashFlow", [("2024-03-31", 120.0), ("2025-03-31", 180.0)]))
    data.update(series("annualFreeCashFlow", [("2024-03-31", 80.0), ("2025-03-31", 120.0)]))
    data.update(series("annualDilutedEPS", [("2024-03-31", 10.0), ("2025-03-31", 15.0)]))
    data.update(series("annualPretaxIncome", [("2024-03-31", 130.0), ("2025-03-31", 190.0)]))
    data.update(series("annualInterestExpense", [("2024-03-31", 20.0), ("2025-03-31", 25.0)]))
    data.update(series("trailingMarketCap", [("2025-06-30", 3000.0)]))
    data.update(series("trailingSharesOutstanding", [("2025-06-30", 10.0)]))
    return data


class TestRatios:
    def test_return_on_equity(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        # 150 / 600 = 25%
        assert profile["profitability"]["return_on_equity_pct"] == pytest.approx(25.0)

    def test_net_margin(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["profitability"]["net_margin_pct"] == pytest.approx(12.5)

    def test_debt_to_equity(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["leverage"]["debt_to_equity"] == pytest.approx(0.5)

    def test_net_debt_subtracts_cash(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["leverage"]["net_debt"] == pytest.approx(200.0)

    def test_current_and_quick_ratio(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["liquidity"]["current_ratio"] == pytest.approx(2.0)
        # (500 - 150) / 250
        assert profile["liquidity"]["quick_ratio"] == pytest.approx(1.4)

    def test_book_value_per_share(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["valuation"]["book_value_per_share"] == pytest.approx(60.0)

    def test_price_to_book(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["valuation"]["price_to_book"] == pytest.approx(5.0)

    def test_roce_uses_ebit(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        # EBIT = pretax 190 + interest 25 = 215; invested capital 900
        assert profile["profitability"]["roce_pct"] == pytest.approx(215 / 900 * 100)

    def test_dupont_reproduces_roe(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["dupont"]["roe_from_dupont_pct"] == pytest.approx(
            profile["profitability"]["return_on_equity_pct"]
        )


class TestGrowth:
    def test_revenue_yoy(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["growth"]["revenue_yoy_pct"] == pytest.approx(20.0)

    def test_net_income_yoy(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["growth"]["net_income_yoy_pct"] == pytest.approx(50.0)

    def test_cagr_needs_enough_years(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        assert profile["growth"]["revenue_cagr_3y_pct"] is None


class TestHealthScore:
    def test_score_is_bounded(self, simple_profile):
        profile = fa.build_fundamentals(simple_profile)
        score = profile["health_score"]["score"]
        assert 0 <= score <= 100
        assert profile["health_score"]["label"] in {"Strong", "Healthy", "Mixed", "Weak"}

    def test_empty_data_scores_zero(self):
        profile = fa.build_fundamentals({})
        assert profile["health_score"]["score"] == 0.0


class TestStatements:
    def test_build_statements_groups_lines(self, simple_profile):
        statements = fa.build_statements(simple_profile, years=5)
        assert statements["period_type"] == "annual"
        assert "revenue" in statements["income_statement"]
        assert "total_assets" in statements["balance_sheet"]
        assert "operating_cash_flow" in statements["cash_flow"]
        assert statements["periods"] == ["2024-03-31", "2025-03-31"]

    def test_series_helper_sorts_ascending(self, simple_profile):
        rows = fa.series_of(simple_profile, "annualTotalRevenue")
        assert rows[0][0] == "2024-03-31"
        assert rows[-1][0] == "2025-03-31"
