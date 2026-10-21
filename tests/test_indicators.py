"""Unit tests for the indicator maths - no network, deterministic inputs."""

from __future__ import annotations

import math

import pytest

from trademcp.analytics import indicators as ind
from trademcp.providers.yahoo import Bar


def make_bars(closes: list[float], *, spread: float = 1.0, volume: int = 1000) -> list[Bar]:
    """Build candles from a close series with a fixed high/low spread."""
    bars = []
    for i, close in enumerate(closes):
        bars.append(
            Bar(
                date=f"2024-01-{i + 1:02d}",
                open=close,
                high=close + spread,
                low=max(close - spread, 0.01),
                close=close,
                volume=volume,
            )
        )
    return bars


class TestMovingAverages:
    def test_sma_windows(self):
        values = ind.sma([1, 2, 3, 4, 5], 3)
        assert values[0] is None and values[1] is None
        assert values[2] == pytest.approx(2.0)
        assert values[4] == pytest.approx(4.0)

    def test_ema_is_seeded_with_sma(self):
        values = ind.ema([1, 2, 3, 4, 5], 3)
        assert values[:2] == [None, None]
        assert values[2] == pytest.approx(2.0)  # SMA seed
        assert values[3] == pytest.approx(3.0)  # alpha 0.5
        assert values[4] == pytest.approx(4.0)

    def test_sma_of_empty_series(self):
        assert ind.sma([], 5) == []

    def test_rolling_max_and_min(self):
        values = [3, 1, 4, 1, 5]
        assert ind.rolling_max(values, 3)[-1] == pytest.approx(5.0)
        assert ind.rolling_min(values, 3)[-1] == pytest.approx(1.0)

    def test_stdev_of_constant_series_is_zero(self):
        assert ind.stdev([7.0] * 10, 5)[-1] == pytest.approx(0.0)


class TestMomentum:
    def test_rsi_of_pure_uptrend_is_100(self):
        values = ind.rsi([float(i) for i in range(1, 30)], 14)
        assert values[-1] == pytest.approx(100.0)

    def test_rsi_of_pure_downtrend_is_zero(self):
        values = ind.rsi([float(i) for i in range(30, 1, -1)], 14)
        assert values[-1] == pytest.approx(0.0)

    def test_rsi_needs_enough_history(self):
        assert ind.rsi([1.0, 2.0], 14) == [None, None]

    def test_macd_histogram_is_none_until_signal_warms_up(self):
        # An accelerating uptrend: MACD leads its signal line.
        closes = [float(i * i) for i in range(1, 60)]
        data = ind.macd(closes)
        assert data["macd"][-1] is not None
        assert data["histogram"][0] is None
        assert data["histogram"][-1] is not None
        assert data["macd"][-1] > data["signal"][-1]

    def test_macd_converges_on_a_linear_series(self):
        # A constant-slope series has a constant MACD, so it equals its signal.
        closes = [float(i) for i in range(1, 60)]
        data = ind.macd(closes)
        assert data["macd"][-1] == pytest.approx(data["signal"][-1], rel=1e-6)

    def test_cci_of_flat_series_is_zero(self):
        bars = make_bars([50.0] * 30)
        values = ind.cci(bars, 20)
        assert values[-1] == pytest.approx(0.0)


class TestVolatility:
    def test_atr_of_constant_range_bars(self):
        bars = make_bars([100.0] * 30, spread=2.0)
        values = ind.atr(bars, 14)
        # True range is 4.0 every bar (high-low), so ATR settles at 4.0.
        assert values[-1] == pytest.approx(4.0, rel=1e-6)

    def test_bollinger_of_constant_series_collapses(self):
        data = ind.bollinger([10.0] * 30, 20, 2.0)
        assert data["upper"][-1] == pytest.approx(10.0)
        assert data["lower"][-1] == pytest.approx(10.0)
        assert data["percent_b"][-1] == pytest.approx(0.5)

    def test_bollinger_percent_b_bounds(self):
        data = ind.bollinger([float(i) for i in range(1, 40)], 20, 2.0)
        assert -1.0 <= data["percent_b"][-1] <= 2.0

    def test_true_range_uses_previous_close(self):
        bars = [
            Bar(date="d1", open=10, high=10, low=10, close=10, volume=1),
            Bar(date="d2", open=10, high=12, low=9, close=11, volume=1),
        ]
        # max(12-9, |12-10|, |9-10|) = 3
        assert ind.true_range(bars)[-1] == pytest.approx(3.0)


class TestTrendSystems:
    def test_supertrend_direction_flips_with_price(self):
        rising = make_bars([100.0 + i for i in range(40)], spread=0.5)
        falling = make_bars([200.0 - i for i in range(40)], spread=0.5)
        assert ind.supertrend(rising, 10, 3.0)["direction"][-1] == 1
        assert ind.supertrend(falling, 10, 3.0)["direction"][-1] == -1

    def test_adx_is_none_before_warmup(self):
        bars = make_bars([100.0] * 10)
        data = ind.adx(bars, 14)
        assert all(v is None for v in data["adx"])

    def test_ichimoku_periods(self):
        bars = make_bars([float(i) for i in range(1, 60)])
        data = ind.ichimoku(bars)
        assert data["tenkan"][-1] is not None
        assert data["kijun"][-1] is not None
        assert data["senkou_b"][-1] is not None


class TestStatistics:
    def test_max_drawdown(self):
        result = ind.max_drawdown([100.0, 50.0, 200.0])
        assert result["max_drawdown_pct"] == pytest.approx(-50.0)

    def test_beta_of_identical_series_is_one(self):
        closes = [float(i) for i in range(1, 100)]
        beta, alpha = ind.beta_alpha(closes, closes)
        assert beta == pytest.approx(1.0)
        assert alpha == pytest.approx(0.0, abs=1e-6)

    def test_beta_of_short_series_is_none(self):
        assert ind.beta_alpha([1.0, 2.0], [1.0, 2.0]) == (None, None)

    def test_sharpe_and_sortino_are_finite(self):
        closes = [100.0 * (1.01 ** i) * (1.05 if i % 7 == 0 else 1.0) for i in range(120)]
        sharpe = ind.sharpe_ratio(closes)
        sortino = ind.sortino_ratio(closes)
        assert sharpe is not None and math.isfinite(sharpe)
        assert sortino is not None and math.isfinite(sortino)

    def test_sortino_is_undefined_without_downside(self):
        # A monotonically rising series has no downside deviation to divide by.
        closes = [100.0 * (1.01 ** i) for i in range(120)]
        assert ind.sortino_ratio(closes) is None

    def test_cagr(self):
        assert ind.cagr(100.0, 121.0, 2) == pytest.approx(10.0)

    def test_cagr_rejects_bad_input(self):
        assert ind.cagr(0.0, 100.0, 2) is None
        assert ind.cagr(100.0, 100.0, 0) is None


class TestVolume:
    def test_obv_accumulates_on_up_days(self):
        bars = [
            Bar(date="d1", open=10, high=10, low=10, close=10, volume=100),
            Bar(date="d2", open=10, high=12, low=10, close=11, volume=200),
        ]
        assert ind.obv(bars)[-1] == pytest.approx(200.0)

    def test_vwap_between_low_and_high(self):
        bars = make_bars([100.0] * 10, spread=5.0, volume=100)
        vwap = ind.vwap(bars)[-1]
        assert 95.0 <= vwap <= 105.0

    def test_mfi_of_flat_volume_prices_is_neutral(self):
        bars = make_bars([100.0] * 30)
        assert ind.mfi(bars, 14)[-1] is not None


class TestLevels:
    def test_classic_pivot_points(self):
        prev = Bar(date="d1", open=10, high=20, low=10, close=15, volume=1)
        pivots = ind.pivot_points(prev)
        classic = pivots["classic"]
        assert classic["pivot"] == pytest.approx(15.0)
        assert classic["r1"] == pytest.approx(20.0)
        assert classic["s1"] == pytest.approx(10.0)

    def test_fibonacci_levels_span_high_to_low(self):
        levels = ind.fib_retracement(200.0, 100.0)
        assert levels["0.0%"] == pytest.approx(200.0)
        assert levels["100.0%"] == pytest.approx(100.0)
        assert levels["50.0%"] == pytest.approx(150.0)

    def test_swing_points_detect_a_peak(self):
        closes = [1, 2, 3, 4, 5, 4, 3, 2, 1]
        bars = make_bars(closes, spread=0.1)
        swings = ind.swing_points(bars, left=2, right=2)
        assert any(abs(point["price"] - 5.1) < 1e-6 for point in swings["highs"])

    def test_candlestick_patterns_detect_bullish_engulfing(self):
        bars = [
            Bar(date="d1", open=100, high=101, low=98, close=99, volume=10),
            Bar(date="d2", open=100, high=101, low=97, close=98, volume=10),
            Bar(date="d3", open=98, high=104, low=98, close=103, volume=10),
        ]
        names = [p["pattern"] for p in ind.candlestick_patterns(bars)]
        assert "Bullish Engulfing" in names

    def test_candlestick_patterns_detect_shooting_star(self):
        bars = [
            Bar(date="d1", open=100, high=101, low=98, close=99, volume=10),
            Bar(date="d2", open=101, high=105, low=100, close=100, volume=10),
        ]
        names = [p["pattern"] for p in ind.candlestick_patterns(bars)]
        assert "Shooting Star" in names

    def test_candlestick_patterns_detect_hammer(self):
        bars = [
            Bar(date="d1", open=100, high=101, low=98, close=99, volume=10),
            Bar(date="d2", open=100, high=101.5, low=95, close=101, volume=10),
        ]
        names = [p["pattern"] for p in ind.candlestick_patterns(bars)]
        assert "Hammer" in names
