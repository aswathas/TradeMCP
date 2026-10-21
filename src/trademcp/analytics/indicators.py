"""Technical indicators, statistics and price levels - pure Python, no numpy.

Every function takes plain lists and returns either a full series aligned with
the input (``None`` where there is not enough history) or a scalar.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from ..providers.yahoo import Bar

Num = float | None


# ---------------------------------------------------------------- moving averages


def sma(values: Sequence[float], period: int) -> list[Num]:
    out: list[Num] = []
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= period:
            total -= values[i - period]
        out.append(total / period if i >= period - 1 else None)
    return out


def ema(values: Sequence[float], period: int) -> list[Num]:
    """EMA seeded with the SMA of the first ``period`` values."""
    out: list[Num] = [None] * len(values)
    if len(values) < period:
        return out
    alpha = 2.0 / (period + 1)
    current = sum(values[:period]) / period
    out[period - 1] = current
    for i in range(period, len(values)):
        current = alpha * values[i] + (1 - alpha) * current
        out[i] = current
    return out


def wilder_rma(values: Sequence[float], period: int) -> list[Num]:
    """Wilder's smoothing (RMA) - the basis of RSI, ATR and ADX."""
    out: list[Num] = [None] * len(values)
    if len(values) < period:
        return out
    current = sum(values[:period]) / period
    out[period - 1] = current
    for i in range(period, len(values)):
        current = (current * (period - 1) + values[i]) / period
        out[i] = current
    return out


def stdev(values: Sequence[float], period: int) -> list[Num]:
    out: list[Num] = []
    for i in range(len(values)):
        if i < period - 1:
            out.append(None)
            continue
        window = values[i - period + 1 : i + 1]
        mean = sum(window) / period
        variance = sum((v - mean) ** 2 for v in window) / period
        out.append(math.sqrt(variance))
    return out


def rolling_max(values: Sequence[float], period: int) -> list[Num]:
    out: list[Num] = []
    for i in range(len(values)):
        out.append(max(values[i - period + 1 : i + 1]) if i >= period - 1 else None)
    return out


def rolling_min(values: Sequence[float], period: int) -> list[Num]:
    out: list[Num] = []
    for i in range(len(values)):
        out.append(min(values[i - period + 1 : i + 1]) if i >= period - 1 else None)
    return out


def zscore(values: Sequence[float], period: int) -> list[Num]:
    means = sma(values, period)
    sds = stdev(values, period)
    out: list[Num] = []
    for i in range(len(values)):
        m, s = means[i], sds[i]
        out.append((values[i] - m) / s if m is not None and s not in (None, 0) else None)
    return out


def linear_slope(values: Sequence[float], period: int) -> list[Num]:
    """Least-squares slope over a rolling window, normalised per bar."""
    out: list[Num] = []
    for i in range(len(values)):
        if i < period - 1:
            out.append(None)
            continue
        window = values[i - period + 1 : i + 1]
        n = len(window)
        mean_x = (n - 1) / 2
        mean_y = sum(window) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(window))
        den = sum((x - mean_x) ** 2 for x in range(n))
        out.append(num / den if den else None)
    return out


# ---------------------------------------------------------------- momentum


def rsi(closes: Sequence[float], period: int = 14) -> list[Num]:
    out: list[Num] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = [max(0.0, closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    losses = [max(0.0, closes[i - 1] - closes[i]) for i in range(1, len(closes))]
    avg_gain = wilder_rma(gains, period)
    avg_loss = wilder_rma(losses, period)
    for i in range(len(gains)):
        if avg_gain[i] is None or avg_loss[i] is None:
            continue
        if avg_loss[i] == 0:
            out[i + 1] = 100.0
        else:
            rs = avg_gain[i] / avg_loss[i]
            out[i + 1] = 100 - (100 / (1 + rs))
    return out


def macd(
    closes: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> dict[str, list[Num]]:
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    line: list[Num] = [
        (f - s) if f is not None and s is not None else None for f, s in zip(fast_ema, slow_ema)
    ]
    defined = [i for i, v in enumerate(line) if v is not None]
    sig: list[Num] = [None] * len(closes)
    hist: list[Num] = [None] * len(closes)
    if defined:
        segment = [line[i] for i in defined]  # type: ignore[misc]
        sig_segment = ema(segment, signal)
        for offset, idx in enumerate(defined):
            sig_value = sig_segment[offset]
            sig[idx] = sig_value
            if sig_value is not None:
                hist[idx] = line[idx] - sig_value  # type: ignore[operator]
    return {"macd": line, "signal": sig, "histogram": hist}


def stochastic(bars: Sequence[Bar], k_period: int = 14, d_period: int = 3) -> dict[str, list[Num]]:
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    closes = [b.close for b in bars]
    hh = rolling_max(highs, k_period)
    ll = rolling_min(lows, k_period)
    k: list[Num] = []
    for i in range(len(bars)):
        if hh[i] is None or ll[i] is None or hh[i] == ll[i]:
            k.append(None)
        else:
            k.append(100 * (closes[i] - ll[i]) / (hh[i] - ll[i]))  # type: ignore[operator]
    d: list[Num] = []
    for i in range(len(k)):
        if i < k_period + d_period - 2:
            d.append(None)
        else:
            window = [v for v in k[i - d_period + 1 : i + 1] if v is not None]
            d.append(sum(window) / len(window) if len(window) == d_period else None)
    return {"k": k, "d": d}


def stoch_rsi(
    closes: Sequence[float], period: int = 14, k_period: int = 3, d_period: int = 3
) -> dict[str, list[Num]]:
    r = rsi(closes, period)
    raw_k: list[Num] = [None] * len(closes)
    for i in range(len(closes)):
        if r[i] is None:
            continue
        window = [v for v in r[i - period + 1 : i + 1] if v is not None]
        if len(window) < period:
            continue
        lo, hi = min(window), max(window)
        raw_k[i] = 0.0 if hi == lo else 100 * (r[i] - lo) / (hi - lo)  # type: ignore[operator]
    k: list[Num] = []
    for i in range(len(raw_k)):
        if i < period + k_period - 2:
            k.append(None)
        else:
            window = [v for v in raw_k[i - k_period + 1 : i + 1] if v is not None]
            k.append(sum(window) / len(window) if len(window) == k_period else None)
    d: list[Num] = []
    for i in range(len(k)):
        if i < k_period + d_period - 2:
            d.append(None)
        else:
            window = [v for v in k[i - d_period + 1 : i + 1] if v is not None]
            d.append(sum(window) / len(window) if len(window) == d_period else None)
    return {"k": k, "d": d}


def cci(bars: Sequence[Bar], period: int = 20) -> list[Num]:
    tp = [(b.high + b.low + b.close) / 3 for b in bars]
    sma_tp = sma(tp, period)
    out: list[Num] = []
    for i in range(len(bars)):
        if sma_tp[i] is None:
            out.append(None)
            continue
        window = tp[i - period + 1 : i + 1]
        mean = sma_tp[i]
        dev = sum(abs(v - mean) for v in window) / period  # type: ignore[operator]
        out.append(0.0 if dev == 0 else (tp[i] - mean) / (0.015 * dev))  # type: ignore[operator]
    return out


def williams_r(bars: Sequence[Bar], period: int = 14) -> list[Num]:
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    hh = rolling_max(highs, period)
    ll = rolling_min(lows, period)
    out: list[Num] = []
    for i, b in enumerate(bars):
        if hh[i] is None or ll[i] is None or hh[i] == ll[i]:
            out.append(None)
        else:
            out.append(-100 * (hh[i] - b.close) / (hh[i] - ll[i]))  # type: ignore[operator]
    return out


def roc(closes: Sequence[float], period: int = 10) -> list[Num]:
    out: list[Num] = []
    for i in range(len(closes)):
        if i < period or closes[i - period] == 0:
            out.append(None)
        else:
            out.append((closes[i] - closes[i - period]) / closes[i - period] * 100)
    return out


def cmo(closes: Sequence[float], period: int = 14) -> list[Num]:
    out: list[Num] = [None] * len(closes)
    for i in range(period, len(closes)):
        gains = losses = 0.0
        for j in range(i - period + 1, i + 1):
            delta = closes[j] - closes[j - 1]
            gains += max(0.0, delta)
            losses += max(0.0, -delta)
        total = gains + losses
        out[i] = 0.0 if total == 0 else 100 * (gains - losses) / total
    return out


def awesome_oscillator(bars: Sequence[Bar], fast: int = 5, slow: int = 34) -> list[Num]:
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    mid = [(h + l) / 2 for h, l in zip(highs, lows)]
    return [
        (a - b) if a is not None and b is not None else None
        for a, b in zip(sma(mid, fast), sma(mid, slow))
    ]


def tsi(closes: Sequence[float], long: int = 25, short: int = 13) -> list[Num]:
    momentum = [0.0] + [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    first = wilder_rma(momentum, long)
    second = [None if f is None else abs(f) for f in first]
    smoothed = wilder_rma([v for v in second if v is not None], short)
    out: list[Num] = [None] * len(closes)
    offset = len(second) - len(smoothed)
    for i, value in enumerate(smoothed):
        if value is None or value == 0:
            continue
        idx = i + offset
        if idx < len(first) and first[idx] is not None:
            out[idx] = 100 * first[idx] / value  # type: ignore[operator]
    return out


def ultimate_oscillator(bars: Sequence[Bar]) -> list[Num]:
    """Bill Lane's 7/14/28 day Ultimate Oscillator."""
    out: list[Num] = [None] * len(bars)
    prev_close = None
    bp_sum = [0.0] * len(bars)
    tr_sum = [0.0] * len(bars)
    for i, b in enumerate(bars):
        if prev_close is None:
            prev_close = b.close
            continue
        true_low = min(b.low, prev_close)
        true_high = max(b.high, prev_close)
        bp_sum[i] = b.close - true_low
        tr_sum[i] = true_high - true_low
        prev_close = b.close

    def average(i: int, period: int) -> float | None:
        if i < period:
            return None
        bp = sum(bp_sum[i - period + 1 : i + 1])
        tr = sum(tr_sum[i - period + 1 : i + 1])
        if tr == 0:
            return None
        return 100 * bp / tr

    for i in range(len(bars)):
        a7, a14, a28 = average(i, 7), average(i, 14), average(i, 28)
        if a7 is None or a14 is None or a28 is None:
            continue
        out[i] = (4 * a7 + 2 * a14 + a28) / 7
    return out


def aroon(bars: Sequence[Bar], period: int = 14) -> dict[str, list[Num]]:
    up: list[Num] = [None] * len(bars)
    down: list[Num] = [None] * len(bars)
    for i in range(len(bars)):
        if i < period:
            continue
        window = bars[i - period : i + 1]
        highs = [b.high for b in window]
        lows = [b.low for b in window]
        idx_high = max(range(len(highs)), key=lambda k: highs[k])
        idx_low = min(range(len(lows)), key=lambda k: lows[k])
        up[i] = 100 * idx_high / period
        down[i] = 100 * idx_low / period
    return {"up": up, "down": down}


def vortex(bars: Sequence[Bar], period: int = 14) -> dict[str, list[Num]]:
    vi_plus: list[Num] = [None] * len(bars)
    vi_minus: list[Num] = [None] * len(bars)
    for i in range(period, len(bars)):
        tr = 0.0
        vm_plus = 0.0
        vm_minus = 0.0
        for j in range(i - period + 1, i + 1):
            prev = bars[j - 1]
            cur = bars[j]
            tr += max(cur.high - cur.low, abs(cur.high - prev.close), abs(cur.low - prev.close))
            vm_plus += abs(cur.high - prev.low)
            vm_minus += abs(cur.low - prev.high)
        if tr:
            vi_plus[i] = 100 * vm_plus / tr
            vi_minus[i] = 100 * vm_minus / tr
    return {"vi_plus": vi_plus, "vi_minus": vi_minus}


# ---------------------------------------------------------------- volatility


def true_range(bars: Sequence[Bar]) -> list[float]:
    out: list[float] = []
    for i, b in enumerate(bars):
        if i == 0:
            out.append(b.high - b.low)
        else:
            prev_close = bars[i - 1].close
            out.append(max(b.high - b.low, abs(b.high - prev_close), abs(b.low - prev_close)))
    return out


def atr(bars: Sequence[Bar], period: int = 14) -> list[Num]:
    return wilder_rma(true_range(bars), period)


def adx(bars: Sequence[Bar], period: int = 14) -> dict[str, list[Num]]:
    """Average Directional Index with +DI and -DI."""
    n = len(bars)
    out: dict[str, list[Num]] = {"adx": [None] * n, "plus_di": [None] * n, "minus_di": [None] * n}
    if n < period * 2:
        return out

    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        up = bars[i].high - bars[i - 1].high
        down = bars[i - 1].low - bars[i].low
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0

    tr_smooth = wilder_rma(true_range(bars), period)
    plus_smooth = wilder_rma(plus_dm, period)
    minus_smooth = wilder_rma(minus_dm, period)

    dx_values: list[float] = []
    dx_index: list[int] = []
    for i in range(n):
        if tr_smooth[i] in (None, 0) or plus_smooth[i] is None or minus_smooth[i] is None:
            continue
        plus_di = 100 * plus_smooth[i] / tr_smooth[i]
        minus_di = 100 * minus_smooth[i] / tr_smooth[i]
        out["plus_di"][i] = plus_di
        out["minus_di"][i] = minus_di
        total = plus_di + minus_di
        dx_values.append(0.0 if total == 0 else 100 * abs(plus_di - minus_di) / total)
        dx_index.append(i)

    if dx_values:
        smoothed = wilder_rma(dx_values, period)
        for offset, value in enumerate(smoothed):
            if value is not None and offset < len(dx_index):
                out["adx"][dx_index[offset]] = value
    return out


def bollinger(closes: Sequence[float], period: int = 20, mult: float = 2.0) -> dict[str, list[Num]]:
    mid = sma(closes, period)
    sd = stdev(closes, period)
    upper: list[Num] = [None] * len(closes)
    lower: list[Num] = [None] * len(closes)
    pct_b: list[Num] = [None] * len(closes)
    bandwidth: list[Num] = [None] * len(closes)
    for i in range(len(closes)):
        if mid[i] is None or sd[i] is None:
            continue
        up = mid[i] + mult * sd[i]
        low = mid[i] - mult * sd[i]
        upper[i] = up
        lower[i] = low
        pct_b[i] = (closes[i] - low) / (up - low) if up != low else 0.5
        bandwidth[i] = (up - low) / mid[i] if mid[i] else None
    return {"middle": mid, "upper": upper, "lower": lower, "percent_b": pct_b, "bandwidth": bandwidth}


def keltner(bars: Sequence[Bar], period: int = 20, mult: float = 2.0, atr_period: int = 10) -> dict[str, list[Num]]:
    closes = [b.close for b in bars]
    mid = ema(closes, period)
    a = atr(bars, atr_period)
    upper: list[Num] = [None] * len(bars)
    lower: list[Num] = [None] * len(bars)
    for i in range(len(bars)):
        if mid[i] is None or a[i] is None:
            continue
        upper[i] = mid[i] + mult * a[i]
        lower[i] = mid[i] - mult * a[i]
    return {"middle": mid, "upper": upper, "lower": lower}


def donchian(bars: Sequence[Bar], period: int = 20) -> dict[str, list[Num]]:
    highs = rolling_max([b.high for b in bars], period)
    lows = rolling_min([b.low for b in bars], period)
    return {"upper": highs, "lower": lows}


def historical_volatility(closes: Sequence[float], period: int = 30, trading_days: int = 252) -> list[Num]:
    returns = [0.0]
    for i in range(1, len(closes)):
        returns.append(math.log(closes[i] / closes[i - 1]) if closes[i - 1] > 0 else 0.0)
    sd = stdev(returns, period)
    return [None if v is None else v * math.sqrt(trading_days) * 100 for v in sd]


# ---------------------------------------------------------------- volume


def obv(bars: Sequence[Bar]) -> list[float]:
    out = [0.0]
    for i in range(1, len(bars)):
        prev, cur = bars[i - 1], bars[i]
        if cur.close > prev.close:
            out.append(out[-1] + cur.volume)
        elif cur.close < prev.close:
            out.append(out[-1] - cur.volume)
        else:
            out.append(out[-1])
    return out


def vwap(bars: Sequence[Bar]) -> list[Num]:
    """Volume weighted average price, anchored at the start of the series."""
    out: list[Num] = []
    cum_pv = 0.0
    cum_v = 0.0
    for b in bars:
        typical = (b.high + b.low + b.close) / 3
        cum_pv += typical * b.volume
        cum_v += b.volume
        out.append(cum_pv / cum_v if cum_v else typical)
    return out


def mfi(bars: Sequence[Bar], period: int = 14) -> list[Num]:
    typical = [(b.high + b.low + b.close) / 3 for b in bars]
    out: list[Num] = [None] * len(bars)
    for i in range(period, len(bars)):
        positive = negative = 0.0
        for j in range(i - period + 1, i + 1):
            flow = typical[j] * bars[j].volume
            if typical[j] > typical[j - 1]:
                positive += flow
            elif typical[j] < typical[j - 1]:
                negative += flow
        if negative == 0:
            out[i] = 100.0
        else:
            out[i] = 100 - (100 / (1 + positive / negative))
    return out


def chaikin_money_flow(bars: Sequence[Bar], period: int = 20) -> list[Num]:
    mfv = []
    for b in bars:
        span = b.high - b.low
        mfm = ((b.close - b.low) - (b.high - b.close)) / span if span else 0.0
        mfv.append(mfm * b.volume)
    out: list[Num] = []
    for i in range(len(bars)):
        if i < period - 1:
            out.append(None)
            continue
        window = mfv[i - period + 1 : i + 1]
        volume = sum(b.volume for b in bars[i - period + 1 : i + 1])
        out.append(sum(window) / volume if volume else None)
    return out


def accumulation_distribution(bars: Sequence[Bar]) -> list[float]:
    out: list[float] = []
    running = 0.0
    for b in bars:
        span = b.high - b.low
        mfm = ((b.close - b.low) - (b.high - b.close)) / span if span else 0.0
        running += mfm * b.volume
        out.append(running)
    return out


def price_volume_trend(bars: Sequence[Bar]) -> list[float]:
    out: list[float] = []
    running = 0.0
    for i, b in enumerate(bars):
        if i == 0:
            out.append(0.0)
            continue
        prev_close = bars[i - 1].close
        running += ((b.close - prev_close) / prev_close) * b.volume if prev_close else 0.0
        out.append(running)
    return out


def force_index(bars: Sequence[Bar], period: int = 13) -> list[Num]:
    raw = []
    for i, b in enumerate(bars):
        if i == 0:
            raw.append(0.0)
        else:
            raw.append((b.close - bars[i - 1].close) * b.volume)
    return ema(raw, period)


def volume_ratio(bars: Sequence[Bar], period: int = 20) -> list[Num]:
    """Current volume relative to its own average."""
    vols = [float(b.volume) for b in bars]
    avg = sma(vols, period)
    return [None if (a is None or a == 0) else v / a for v, a in zip(vols, avg)]


# ---------------------------------------------------------------- trend systems


def supertrend(bars: Sequence[Bar], period: int = 10, mult: float = 3.0) -> dict[str, list[Any]]:
    n = len(bars)
    a = atr(bars, period)
    line: list[Num] = [None] * n
    direction: list[int | None] = [None] * n
    if n <= period:
        return {"line": line, "direction": direction}

    final_upper = [0.0] * n
    final_lower = [0.0] * n
    for i in range(period, n):
        atr_i = a[i]
        if atr_i is None:
            continue
        hl2 = (bars[i].high + bars[i].low) / 2
        basic_upper = hl2 + mult * atr_i
        basic_lower = hl2 - mult * atr_i
        if i == period or final_upper[i - 1] == 0:
            final_upper[i] = basic_upper
            final_lower[i] = basic_lower
            direction[i] = 1 if bars[i].close >= hl2 else -1
        else:
            prev_close = bars[i - 1].close
            final_upper[i] = (
                basic_upper
                if basic_upper < final_upper[i - 1] or prev_close > final_upper[i - 1]
                else final_upper[i - 1]
            )
            final_lower[i] = (
                basic_lower
                if basic_lower > final_lower[i - 1] or prev_close < final_lower[i - 1]
                else final_lower[i - 1]
            )
            if direction[i - 1] == 1 and bars[i].close <= final_upper[i]:
                direction[i] = -1
            elif direction[i - 1] == -1 and bars[i].close >= final_lower[i]:
                direction[i] = 1
            else:
                direction[i] = direction[i - 1]
        line[i] = final_lower[i] if direction[i] == 1 else final_upper[i]
    return {"line": line, "direction": direction}


def ichimoku(bars: Sequence[Bar]) -> dict[str, list[Num]]:
    n = len(bars)
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    closes = [b.close for b in bars]

    def mid(period: int) -> list[Num]:
        hh = rolling_max(highs, period)
        ll = rolling_min(lows, period)
        return [None if hh[i] is None or ll[i] is None else (hh[i] + ll[i]) / 2 for i in range(n)]  # type: ignore[operator]

    tenkan = mid(9)
    kijun = mid(26)
    senkou_b = mid(52)
    span_a: list[Num] = [None] * n
    span_b: list[Num] = [None] * n
    chikou: list[Num] = [None] * n
    for i in range(n):
        if tenkan[i] is not None and kijun[i] is not None:
            span_a[i] = (tenkan[i] + kijun[i]) / 2  # type: ignore[operator]
        if senkou_b[i] is not None:
            span_b[i] = senkou_b[i]
        if i >= 26:
            chikou[i] = closes[i - 26]
    return {"tenkan": tenkan, "kijun": kijun, "senkou_a": span_a, "senkou_b": span_b, "chikou": chikou}


def psar(bars: Sequence[Bar], step: float = 0.02, max_af: float = 0.2) -> list[Num]:
    """Parabolic SAR."""
    n = len(bars)
    if n < 2:
        return [None] * n
    out: list[Num] = [None] * n
    bull = bars[1].close >= bars[0].close
    sar = bars[0].low if bull else bars[0].high
    ep = bars[1].high if bull else bars[1].low
    af = step
    out[1] = sar
    for i in range(2, n):
        sar = sar + af * (ep - sar)
        if bull:
            sar = min(sar, bars[i - 1].low, bars[i - 2].low if i >= 2 else bars[i - 1].low)
            if bars[i].low < sar:
                bull = False
                sar = ep
                ep = bars[i].low
                af = step
            elif bars[i].high > ep:
                ep = bars[i].high
                af = min(af + step, max_af)
        else:
            sar = max(sar, bars[i - 1].high, bars[i - 2].high if i >= 2 else bars[i - 1].high)
            if bars[i].high > sar:
                bull = True
                sar = ep
                ep = bars[i].high
                af = step
            elif bars[i].low < ep:
                ep = bars[i].low
                af = min(af + step, max_af)
        out[i] = sar
    return out


# ---------------------------------------------------------------- statistics


def daily_returns(closes: Sequence[float]) -> list[float]:
    out = [0.0]
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        out.append((closes[i] - prev) / prev if prev else 0.0)
    return out


def beta_alpha(
    stock_closes: Sequence[float], bench_closes: Sequence[float]
) -> tuple[float | None, float | None]:
    """Beta and annualised alpha of the stock against a benchmark."""
    n = min(len(stock_closes), len(bench_closes))
    if n < 30:
        return None, None
    stock = list(stock_closes[-n:])
    bench = list(bench_closes[-n:])
    rs = daily_returns(stock)[1:]
    rb = daily_returns(bench)[1:]
    mean_s, mean_b = sum(rs) / len(rs), sum(rb) / len(rb)
    cov = sum((s - mean_s) * (b - mean_b) for s, b in zip(rs, rb)) / (len(rs) - 1)
    var_b = sum((b - mean_b) ** 2 for b in rb) / (len(rb) - 1)
    if var_b == 0:
        return None, None
    beta = cov / var_b
    alpha = (mean_s - beta * mean_b) * 252
    return beta, alpha


def sharpe_ratio(closes: Sequence[float], risk_free: float = 0.0, periods: int = 252) -> float | None:
    returns = daily_returns(closes)[1:]
    if len(returns) < 30:
        return None
    mean = sum(returns) / len(returns)
    sd_series = stdev(returns, len(returns))
    sd = sd_series[-1] if sd_series else None
    if not sd:
        return None
    return (mean * periods - risk_free) / (sd * math.sqrt(periods))


def sortino_ratio(closes: Sequence[float], risk_free: float = 0.0, periods: int = 252) -> float | None:
    returns = daily_returns(closes)[1:]
    if len(returns) < 30:
        return None
    mean = sum(returns) / len(returns)
    downside = [r for r in returns if r < 0]
    if not downside:
        return None
    dd = math.sqrt(sum(r * r for r in downside) / len(downside))
    if dd == 0:
        return None
    return (mean * periods - risk_free) / (dd * math.sqrt(periods))


def max_drawdown(closes: Sequence[float]) -> dict[str, float | None]:
    peak = -math.inf
    worst = 0.0
    peak_idx = trough_idx = 0
    best_peak = 0
    for i, c in enumerate(closes):
        if c > peak:
            peak = c
            best_peak = i
        drawdown = (c - peak) / peak if peak else 0.0
        if drawdown < worst:
            worst = drawdown
            peak_idx = best_peak
            trough_idx = i
    return {
        "max_drawdown_pct": worst * 100,
        "peak_index": peak_idx,
        "trough_index": trough_idx,
    }


def cagr(first: float, last: float, years: float) -> float | None:
    if first <= 0 or years <= 0:
        return None
    return ((last / first) ** (1 / years) - 1) * 100


# ---------------------------------------------------------------- price levels


def pivot_points(prev: Bar) -> dict[str, dict[str, float]]:
    """Classic, Camarilla, Fibonacci, Woodie and DeMark pivots from the prior bar."""
    h, l, c = prev.high, prev.low, prev.close
    out: dict[str, dict[str, float]] = {}

    p = (h + l + c) / 3
    out["classic"] = {
        "pivot": p,
        "r1": 2 * p - l,
        "r2": p + (h - l),
        "r3": h + 2 * (p - l),
        "s1": 2 * p - h,
        "s2": p - (h - l),
        "s3": l - 2 * (h - p),
    }

    span = h - l
    out["camarilla"] = {
        "r1": c + span * 1.1 / 12,
        "r2": c + span * 1.1 / 6,
        "r3": c + span * 1.1 / 4,
        "r4": c + span * 1.1 / 2,
        "s1": c - span * 1.1 / 12,
        "s2": c - span * 1.1 / 6,
        "s3": c - span * 1.1 / 4,
        "s4": c - span * 1.1 / 2,
    }

    out["fibonacci"] = {
        "pivot": p,
        "r1": p + 0.382 * span,
        "r2": p + 0.618 * span,
        "r3": p + 1.0 * span,
        "s1": p - 0.382 * span,
        "s2": p - 0.618 * span,
        "s3": p - 1.0 * span,
    }

    wp = (h + l + 2 * c) / 4
    out["woodie"] = {
        "pivot": wp,
        "r1": 2 * wp - l,
        "r2": wp + (h - l),
        "s1": 2 * wp - h,
        "s2": wp - (h - l),
    }

    if c < prev.open:
        x = h + l + 2 * c
        out["demark"] = {"r1": x / 4, "s1": x / 2 - l, "s2": x / 2 - h}
    elif c > prev.open:
        x = 2 * h + l + c
        out["demark"] = {"r1": x / 4, "s1": x / 2 - h, "s2": x / 2 - l}
    else:
        out["demark"] = {"r1": c, "s1": l, "s2": h}

    return out


def fib_retracement(high: float, low: float) -> dict[str, float]:
    span = high - low
    return {
        "0.0%": high,
        "23.6%": high - 0.236 * span,
        "38.2%": high - 0.382 * span,
        "50.0%": high - 0.5 * span,
        "61.8%": high - 0.618 * span,
        "78.6%": high - 0.786 * span,
        "100.0%": low,
    }


def swing_points(bars: Sequence[Bar], left: int = 3, right: int = 3) -> dict[str, list[dict[str, Any]]]:
    """Fractal swing highs and lows."""
    highs: list[dict[str, Any]] = []
    lows: list[dict[str, Any]] = []
    for i in range(left, len(bars) - right):
        window = bars[i - left : i + right + 1]
        if bars[i].high == max(b.high for b in window):
            highs.append({"date": bars[i].date, "price": bars[i].high})
        if bars[i].low == min(b.low for b in window):
            lows.append({"date": bars[i].date, "price": bars[i].low})
    return {"highs": highs[-10:], "lows": lows[-10:]}


# ---------------------------------------------------------------- candles


def _body(b: Bar) -> float:
    return abs(b.close - b.open)


def _is_bullish(b: Bar) -> bool:
    return b.close > b.open


def _upper_wick(b: Bar) -> float:
    return b.high - max(b.open, b.close)


def _lower_wick(b: Bar) -> float:
    return min(b.open, b.close) - b.low


def candlestick_patterns(bars: Sequence[Bar]) -> list[dict[str, Any]]:
    """Detect classic candlestick patterns in the most recent bars."""
    found: list[dict[str, Any]] = []
    n = len(bars)
    if n < 2:
        return found

    for i in range(max(1, n - 10), n):
        cur, prev = bars[i], bars[i - 1]
        body, rng = _body(cur), cur.high - cur.low
        if rng == 0:
            continue
        upper, lower = _upper_wick(cur), _lower_wick(cur)

        def add(name: str, bias: str, note: str) -> None:
            found.append({"pattern": name, "date": cur.date, "bias": bias, "note": note})

        if body < rng * 0.1:
            if lower > body * 2 and upper < body:
                add("Dragonfly Doji", "bullish", "Long lower shadow - rejection of lows")
            elif upper > body * 2 and lower < body:
                add("Gravestone Doji", "bearish", "Long upper shadow - rejection of highs")
            else:
                add("Doji", "neutral", "Indecision - open and close nearly equal")

        # Textbook wick definitions: a shadow >= 2x the body and >= 50% of the range.
        if lower >= body * 2 and lower >= rng * 0.5 and upper <= rng * 0.2 and _is_bullish(cur):
            add("Hammer", "bullish", "Long lower shadow shows buyers stepped in")
        if upper >= body * 2 and upper >= rng * 0.5 and lower <= rng * 0.2 and not _is_bullish(cur):
            add("Shooting Star", "bearish", "Long upper shadow shows sellers hitting highs")
        if upper >= body * 2 and upper >= rng * 0.5 and lower <= rng * 0.2 and _is_bullish(cur):
            add("Inverted Hammer", "bullish", "Long upper shadow on a rising body - possible bottom")

        # Engulfing
        if (
            _is_bullish(cur)
            and not _is_bullish(prev)
            and cur.close >= prev.open
            and cur.open <= prev.close
            and body > _body(prev)
        ):
            add("Bullish Engulfing", "bullish", "Buyers wiped out the prior session's sellers")
        if (
            not _is_bullish(cur)
            and _is_bullish(prev)
            and cur.close <= prev.open
            and cur.open >= prev.close
            and body > _body(prev)
        ):
            add("Bearish Engulfing", "bearish", "Sellers wiped out the prior session's buyers")

        # Harami
        if (
            body < _body(prev) * 0.5
            and cur.high <= prev.high
            and cur.low >= prev.low
            and not (_is_bullish(cur) == _is_bullish(prev))
        ):
            add("Harami", "neutral", "Inside day - momentum fading")

        # Piercing line / dark cloud cover
        if (
            not _is_bullish(prev)
            and _is_bullish(cur)
            and prev.close < cur.open < prev.open
            and cur.close > (prev.open + prev.close) / 2
        ):
            add("Piercing Line", "bullish", "Bulls recovered over half the prior loss")
        if (
            _is_bullish(prev)
            and not _is_bullish(cur)
            and prev.close > cur.open < prev.open
            and cur.close < (prev.open + prev.close) / 2
        ):
            add("Dark Cloud Cover", "bearish", "Bears reversed more than half the prior gain")

        # Three white soldiers / three black crows
        if i >= 2:
            a, b2, c3 = bars[i - 2], bars[i - 1], cur
            if (
                _is_bullish(a)
                and _is_bullish(b2)
                and _is_bullish(c3)
                and b2.close > a.close
                and c3.close > b2.close
                and _body(c3) > _body(b2) > _body(a)
            ):
                add("Three White Soldiers", "bullish", "Three consecutive strong up days")
            if (
                not _is_bullish(a)
                and not _is_bullish(b2)
                and not _is_bullish(c3)
                and b2.close < a.close
                and c3.close < b2.close
                and _body(c3) > _body(b2) > _body(a)
            ):
                add("Three Black Crows", "bearish", "Three consecutive strong down days")

        # Morning / evening star
        if i >= 2:
            a, b2, c3 = bars[i - 2], bars[i - 1], cur
            if (
                not _is_bullish(a)
                and _body(b2) < _body(a) * 0.5
                and _is_bullish(c3)
                and c3.close > (a.open + a.close) / 2
            ):
                add("Morning Star", "bullish", "Down day, indecision, then a strong up day")
            if (
                _is_bullish(a)
                and _body(b2) < _body(a) * 0.5
                and not _is_bullish(c3)
                and c3.close < (a.open + a.close) / 2
            ):
                add("Evening Star", "bearish", "Up day, indecision, then a strong down day")

        # Marubozu
        if body > rng * 0.9:
            add(
                "Bullish Marubozu" if _is_bullish(cur) else "Bearish Marubozu",
                "bullish" if _is_bullish(cur) else "bearish",
                "Long body with almost no wicks",
            )

        # Tweezer top / bottom
        if i >= 1:
            if abs(cur.high - prev.high) < rng * 0.05 and _is_bullish(cur) and not _is_bullish(prev):
                add("Tweezer Top", "bearish", "Two sessions failed at the same high")
            if abs(cur.low - prev.low) < rng * 0.05 and not _is_bullish(cur) and _is_bullish(prev):
                add("Tweezer Bottom", "bullish", "Two sessions held the same low")

    return found
