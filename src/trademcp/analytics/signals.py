"""Turn raw indicator values into directional signals and a composite score."""

from __future__ import annotations

from typing import Any

from ..providers.yahoo import Bar
from . import indicators as ind


def _last(series: list[Any]) -> float | None:
    for value in reversed(series):
        if value is not None:
            return float(value)
    return None


def _signal(name: str, value: float | None, bias: str, strength: float, note: str) -> dict[str, Any]:
    return {
        "indicator": name,
        "value": None if value is None else round(value, 4),
        "signal": bias,
        "strength": strength,
        "note": note,
    }


def technical_signals(bars: list[Bar], benchmark: list[Bar] | None = None) -> dict[str, Any]:
    """Compute every indicator for a series and score the directional bias.

    Args:
        bars: OHLCV candles, oldest first
        benchmark: optional benchmark candles for beta/relative strength

    Returns:
        The indicator values, per-indicator signals and a composite score.
    """
    if not bars:
        return {"signals": [], "summary": {}}

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [float(b.volume) for b in bars]
    price = closes[-1]

    rsi_series = ind.rsi(closes, 14)
    macd_data = ind.macd(closes)
    adx_data = ind.adx(bars, 14)
    st_data = ind.supertrend(bars, 10, 3.0)
    bb = ind.bollinger(closes, 20, 2.0)
    stoch = ind.stochastic(bars, 14, 3)
    cci_series = ind.cci(bars, 20)
    wr_series = ind.williams_r(bars, 14)
    mfi_series = ind.mfi(bars, 14)
    roc_series = ind.roc(closes, 10)
    uo_series = ind.ultimate_oscillator(bars)
    ao_series = ind.awesome_oscillator(bars)
    psar_series = ind.psar(bars)
    ichi = ind.ichimoku(bars)
    vwap_series = ind.vwap(bars)
    atr_series = ind.atr(bars, 14)
    obv_series = ind.obv(bars)
    vwap_vals = vwap_series
    sma20 = ind.sma(closes, 20)
    sma50 = ind.sma(closes, 50)
    sma200 = ind.sma(closes, 200)
    ema20 = ind.ema(closes, 20)
    ema50 = ind.ema(closes, 50)
    vol_ratio = ind.volume_ratio(bars, 20)

    rsi = _last(rsi_series)
    macd_line = _last(macd_data["macd"])
    macd_signal = _last(macd_data["signal"])
    macd_hist = _last(macd_data["histogram"])
    adx = _last(adx_data["adx"])
    plus_di = _last(adx_data["plus_di"])
    minus_di = _last(adx_data["minus_di"])
    st_line = _last(st_data["line"])
    st_dir = next((d for d in reversed(st_data["direction"]) if d is not None), None)
    bb_upper = _last(bb["upper"])
    bb_lower = _last(bb["lower"])
    bb_mid = _last(bb["middle"])
    pct_b = _last(bb["percent_b"])
    stoch_k = _last(stoch["k"])
    stoch_d = _last(stoch["d"])
    cci = _last(cci_series)
    williams = _last(wr_series)
    mfi = _last(mfi_series)
    roc = _last(roc_series)
    uo = _last(uo_series)
    ao = _last(ao_series)
    psar = _last(psar_series)
    tenkan = _last(ichi["tenkan"])
    kijun = _last(ichi["kijun"])
    span_a = _last(ichi["senkou_a"])
    span_b = _last(ichi["senkou_b"])
    vwap = _last(vwap_vals)
    atr_value = _last(atr_series)
    sma20v, sma50v, sma200v = _last(sma20), _last(sma50), _last(sma200)
    ema20v, ema50v = _last(ema20), _last(ema50)
    volr = _last(vol_ratio)

    signals: list[dict[str, Any]] = []

    # --- trend
    if sma50v and sma200v:
        if price > sma50v > sma200v:
            signals.append(_signal("SMA alignment", price, "bullish", 3, "Price > 50 SMA > 200 SMA - clean uptrend"))
        elif price < sma50v < sma200v:
            signals.append(_signal("SMA alignment", price, "bearish", 3, "Price < 50 SMA < 200 SMA - clean downtrend"))
        else:
            signals.append(_signal("SMA alignment", price, "neutral", 1, "Moving averages are tangled"))
    if sma20v and sma50v:
        if sma20v > sma50v:
            signals.append(_signal("SMA 20/50 crossover", sma20v, "bullish", 2, "20 SMA above 50 SMA"))
        else:
            signals.append(_signal("SMA 20/50 crossover", sma20v, "bearish", 2, "20 SMA below 50 SMA"))
    if ema20v and ema50v:
        signals.append(
            _signal("EMA 20/50", ema20v, "bullish" if ema20v > ema50v else "bearish", 2,
                    "Short-term EMA above/below the long-term EMA")
        )
    if st_dir is not None:
        signals.append(
            _signal("Supertrend", st_line, "bullish" if st_dir == 1 else "bearish", 3,
                    f"Supertrend is {'above' if st_dir == 1 else 'below'} price")
        )
    if psar is not None:
        signals.append(
            _signal("Parabolic SAR", psar, "bullish" if price > psar else "bearish", 2,
                    "Price trading above/below the SAR stop")
        )
    if tenkan is not None and kijun is not None:
        signals.append(
            _signal("Ichimoku cross", tenkan, "bullish" if tenkan > kijun else "bearish", 2,
                    "Tenkan-sen above/below Kijun-sen")
        )
    if span_a is not None and span_b is not None:
        above = price > max(span_a, span_b)
        below = price < min(span_a, span_b)
        signals.append(
            _signal("Ichimoku cloud", price, "bullish" if above else ("bearish" if below else "neutral"), 2,
                    "Price above/below/inside the Kumo cloud")
        )
    if adx is not None and plus_di is not None and minus_di is not None:
        strong = adx >= 25
        bias = "bullish" if plus_di > minus_di else "bearish"
        signals.append(
            _signal("ADX / DMI", adx, bias if strong else "neutral", 3 if strong else 1,
                    f"ADX {adx:.1f} ({'strong' if strong else 'weak'} trend), +DI {plus_di:.1f} vs -DI {minus_di:.1f}")
        )

    # --- momentum
    if rsi is not None:
        if rsi >= 70:
            signals.append(_signal("RSI (14)", rsi, "bearish", 2, "Overbought - stretched to the upside"))
        elif rsi <= 30:
            signals.append(_signal("RSI (14)", rsi, "bullish", 2, "Oversold - stretched to the downside"))
        else:
            signals.append(_signal("RSI (14)", rsi, "bullish" if rsi > 50 else "bearish", 1,
                                    f"RSI {rsi:.1f} is {'above' if rsi > 50 else 'below'} the midline"))
    if macd_line is not None and macd_signal is not None:
        signals.append(
            _signal("MACD (12,26,9)", macd_hist, "bullish" if macd_line > macd_signal else "bearish", 3,
                    f"MACD {macd_line:.2f} {'above' if macd_line > macd_signal else 'below'} signal {macd_signal:.2f}")
        )
    if stoch_k is not None:
        if stoch_k >= 80:
            signals.append(_signal("Stochastic %K", stoch_k, "bearish", 2, "Overbought territory"))
        elif stoch_k <= 20:
            signals.append(_signal("Stochastic %K", stoch_k, "bullish", 2, "Oversold territory"))
        else:
            signals.append(_signal("Stochastic %K", stoch_k, "bullish" if stoch_k > stoch_d else "bearish", 1,
                                    "%K vs %D crossover"))
    if cci is not None:
        signals.append(_signal("CCI (20)", cci, "bullish" if cci > 0 else "bearish", 2,
                                "Above zero - buyers in control" if cci > 0 else "Below zero - sellers in control"))
    if williams is not None:
        if williams <= -80:
            signals.append(_signal("Williams %R", williams, "bullish", 2, "Oversold"))
        elif williams >= -20:
            signals.append(_signal("Williams %R", williams, "bearish", 2, "Overbought"))
    if mfi is not None:
        if mfi >= 80:
            signals.append(_signal("Money Flow Index", mfi, "bearish", 2, "Money flow overbought"))
        elif mfi <= 20:
            signals.append(_signal("Money Flow Index", mfi, "bullish", 2, "Money flow oversold"))
    if roc is not None:
        signals.append(_signal("ROC (10)", roc, "bullish" if roc > 0 else "bearish", 2,
                                f"10-day rate of change {roc:+.1f}%"))
    if uo is not None:
        signals.append(_signal("Ultimate Oscillator", uo, "bullish" if uo > 50 else "bearish", 2,
                                f"UO at {uo:.1f}"))
    if ao is not None:
        signals.append(_signal("Awesome Oscillator", ao, "bullish" if ao > 0 else "bearish", 1,
                                "5/34 median price spread"))

    # --- volatility / position
    if pct_b is not None:
        if pct_b > 1:
            signals.append(_signal("Bollinger %B", pct_b, "bearish", 1, "Above the upper band - overextended"))
        elif pct_b < 0:
            signals.append(_signal("Bollinger %B", pct_b, "bullish", 1, "Below the lower band - oversold"))
        else:
            signals.append(_signal("Bollinger %B", pct_b, "neutral", 1, "Inside the bands"))
    if vwap is not None:
        signals.append(_signal("VWAP", vwap, "bullish" if price > vwap else "bearish", 2,
                                "Price above/below the volume-weighted average"))
    if atr_value is not None:
        signals.append(_signal("ATR (14)", atr_value, "neutral", 0,
                                f"Daily range ~{atr_value:.2f} ({atr_value / price * 100:.1f}% of price)"))
    if volr is not None:
        signals.append(_signal("Volume vs 20d average", volr, "neutral", 1,
                                f"Volume running at {volr:.2f}x its 20-day average"))

    # --- volume flow
    if len(obv_series) > 21:
        recent = obv_series[-1] - obv_series[-21]
        signals.append(_signal("OBV (21d change)", recent, "bullish" if recent > 0 else "bearish", 2,
                                "Accumulation" if recent > 0 else "Distribution"))

    score = 0
    for sig in signals:
        if sig["signal"] == "bullish":
            score += sig["strength"]
        elif sig["signal"] == "bearish":
            score -= sig["strength"]

    max_score = sum(s["strength"] for s in signals) or 1
    normalized = round(100 * score / max_score, 1)
    if normalized >= 45:
        label = "Strong Buy"
    elif normalized >= 15:
        label = "Buy"
    elif normalized > -15:
        label = "Neutral"
    elif normalized > -45:
        label = "Sell"
    else:
        label = "Strong Sell"

    bullish = sum(1 for s in signals if s["signal"] == "bullish")
    bearish = sum(1 for s in signals if s["signal"] == "bearish")
    neutral = sum(1 for s in signals if s["signal"] == "neutral")

    indicators = {
        "price": price,
        "sma_20": sma20v,
        "sma_50": sma50v,
        "sma_200": sma200v,
        "ema_20": ema20v,
        "ema_50": ema50v,
        "rsi_14": rsi,
        "macd": macd_line,
        "macd_signal": macd_signal,
        "macd_histogram": macd_hist,
        "adx_14": adx,
        "plus_di": plus_di,
        "minus_di": minus_di,
        "supertrend": st_line,
        "supertrend_direction": "bullish" if st_dir == 1 else ("bearish" if st_dir == -1 else None),
        "parabolic_sar": psar,
        "bollinger_upper": bb_upper,
        "bollinger_middle": bb_mid,
        "bollinger_lower": bb_lower,
        "bollinger_percent_b": pct_b,
        "stochastic_k": stoch_k,
        "stochastic_d": stoch_d,
        "cci_20": cci,
        "williams_r": williams,
        "money_flow_index": mfi,
        "roc_10": roc,
        "ultimate_oscillator": uo,
        "awesome_oscillator": ao,
        "vwap": vwap,
        "atr_14": atr_value,
        "volume_ratio_20": volr,
        "ichimoku_tenkan": tenkan,
        "ichimoku_kijun": kijun,
    }

    statistics: dict[str, Any] = {}
    if len(closes) > 30:
        returns = ind.daily_returns(closes)
        sd = ind.stdev(returns, len(returns))
        statistics = {
            "annualised_volatility_pct": round(sd[-1] * (252 ** 0.5) * 100, 2) if sd[-1] else None,
            "sharpe_ratio": _round(ind.sharpe_ratio(closes)),
            "sortino_ratio": _round(ind.sortino_ratio(closes)),
            "max_drawdown_pct": round(ind.max_drawdown(closes)["max_drawdown_pct"] or 0, 2),
        }
    if benchmark and len(benchmark) > 30:
        bench_closes = [b.close for b in benchmark]
        beta, alpha = ind.beta_alpha(closes, bench_closes)
        bench_return = (bench_closes[-1] / bench_closes[-30] - 1) * 100 if len(bench_closes) >= 30 else None
        stock_return = (closes[-1] / closes[-30] - 1) * 100 if len(closes) >= 30 else None
        statistics.update(
            {
                "beta": _round(beta),
                "annualised_alpha_pct": _round(alpha),
                "return_30d_pct": _round(stock_return),
                "benchmark_return_30d_pct": _round(bench_return),
                "relative_strength_30d_pct": _round((stock_return or 0) - (bench_return or 0)),
            }
        )

    return {
        "indicators": indicators,
        "signals": signals,
        "statistics": statistics,
        "summary": {
            "score": normalized,
            "label": label,
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "total_signals": len(signals),
        },
        "candles": ind.candlestick_patterns(bars),
    }


def _round(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(value, digits)


def support_resistance(bars: list[Bar]) -> dict[str, Any]:
    """Pivot levels, Fibonacci retracements and swing extremes."""
    if len(bars) < 2:
        return {}

    prev = bars[-2]
    price = bars[-1].close
    pivots = ind.pivot_points(prev)

    window = bars[-252:] if len(bars) >= 252 else bars
    period_high = max(b.high for b in window)
    period_low = min(b.low for b in window)
    swing = ind.swing_points(bars)

    return {
        "price": price,
        "as_of": bars[-1].date,
        "pivots": pivots,
        "fibonacci_retracement": ind.fib_retracement(period_high, period_low),
        "range": {
            "period_high": period_high,
            "period_low": period_low,
            "period_days": len(window),
            "position_in_range_pct": round((price - period_low) / (period_high - period_low) * 100, 2)
            if period_high > period_low
            else None,
        },
        "swing_highs": swing["highs"],
        "swing_lows": swing["lows"],
        "donchian_20": ind.donchian(bars, 20),
        "volatility": {
            "atr_14": _last(ind.atr(bars, 14)),
            "bollinger_width_pct": _round(
                ((_last(ind.bollinger([b.close for b in bars], 20, 2.0)["upper"]) or 0)
                 - (_last(ind.bollinger([b.close for b in bars], 20, 2.0)["lower"]) or 0))
                / price * 100
                if price
                else None
            ),
        },
    }
