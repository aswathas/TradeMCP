"""Technical analysis tools: indicator series, signal analysis, price levels."""

from __future__ import annotations

from typing import Annotated, Any, Callable

from pydantic import Field

from ..analytics import indicators as ind
from ..analytics import signals as sg
from ..app import mcp
from ..http import DataSourceError
from ..providers import yahoo
from ..symbols import SymbolNotFound, resolve
from .common import ResponseFormat, error_text, render, tool_annotations


def _fmt_field(description: str):
    return Field(description=description)


def _build_registry() -> dict[str, Callable[[list[Any]], list[Any]]]:
    """name -> function returning a series aligned with the candles."""
    closes = lambda bars: [b.close for b in bars]  # noqa: E731

    registry: dict[str, Callable[[list[Any]], list[Any]]] = {
        "sma_20": lambda b: ind.sma(closes(b), 20),
        "sma_50": lambda b: ind.sma(closes(b), 50),
        "sma_200": lambda b: ind.sma(closes(b), 200),
        "ema_9": lambda b: ind.ema(closes(b), 9),
        "ema_21": lambda b: ind.ema(closes(b), 21),
        "ema_50": lambda b: ind.ema(closes(b), 50),
        "ema_200": lambda b: ind.ema(closes(b), 200),
        "rsi_14": lambda b: ind.rsi(closes(b), 14),
        "rsi_7": lambda b: ind.rsi(closes(b), 7),
        "macd": lambda b: ind.macd(closes(b))["macd"],
        "macd_signal": lambda b: ind.macd(closes(b))["signal"],
        "macd_histogram": lambda b: ind.macd(closes(b))["histogram"],
        "adx_14": lambda b: ind.adx(b, 14)["adx"],
        "plus_di": lambda b: ind.adx(b, 14)["plus_di"],
        "minus_di": lambda b: ind.adx(b, 14)["minus_di"],
        "atr_14": lambda b: ind.atr(b, 14),
        "true_range": lambda b: ind.true_range(b),
        "bollinger_upper": lambda b: ind.bollinger(closes(b))["upper"],
        "bollinger_middle": lambda b: ind.bollinger(closes(b))["middle"],
        "bollinger_lower": lambda b: ind.bollinger(closes(b))["lower"],
        "bollinger_percent_b": lambda b: ind.bollinger(closes(b))["percent_b"],
        "bollinger_bandwidth": lambda b: ind.bollinger(closes(b))["bandwidth"],
        "keltner_upper": lambda b: ind.keltner(b)["upper"],
        "keltner_lower": lambda b: ind.keltner(b)["lower"],
        "stochastic_k": lambda b: ind.stochastic(b)["k"],
        "stochastic_d": lambda b: ind.stochastic(b)["d"],
        "stoch_rsi_k": lambda b: ind.stoch_rsi(closes(b))["k"],
        "cci_20": lambda b: ind.cci(b, 20),
        "williams_r": lambda b: ind.williams_r(b, 14),
        "mfi_14": lambda b: ind.mfi(b, 14),
        "roc_10": lambda b: ind.roc(closes(b), 10),
        "cmo_14": lambda b: ind.cmo(closes(b), 14),
        "ultimate_oscillator": lambda b: ind.ultimate_oscillator(b),
        "awesome_oscillator": lambda b: ind.awesome_oscillator(b),
        "tsi": lambda b: ind.tsi(closes(b)),
        "aroon_up": lambda b: ind.aroon(b)["up"],
        "aroon_down": lambda b: ind.aroon(b)["down"],
        "vortex_plus": lambda b: ind.vortex(b)["vi_plus"],
        "vortex_minus": lambda b: ind.vortex(b)["vi_minus"],
        "supertrend": lambda b: ind.supertrend(b)["line"],
        "parabolic_sar": lambda b: ind.psar(b),
        "ichimoku_tenkan": lambda b: ind.ichimoku(b)["tenkan"],
        "ichimoku_kijun": lambda b: ind.ichimoku(b)["kijun"],
        "ichimoku_senkou_a": lambda b: ind.ichimoku(b)["senkou_a"],
        "ichimoku_senkou_b": lambda b: ind.ichimoku(b)["senkou_b"],
        "vwap": lambda b: ind.vwap(b),
        "obv": lambda b: ind.obv(b),
        "chaikin_money_flow": lambda b: ind.chaikin_money_flow(b),
        "accumulation_distribution": lambda b: ind.accumulation_distribution(b),
        "price_volume_trend": lambda b: ind.price_volume_trend(b),
        "force_index": lambda b: ind.force_index(b),
        "volume_ratio_20": lambda b: ind.volume_ratio(b, 20),
        "historical_volatility": lambda b: ind.historical_volatility(closes(b)),
        "zscore_20": lambda b: ind.zscore(closes(b), 20),
        "linear_slope_20": lambda b: ind.linear_slope(closes(b), 20),
        "donchian_upper": lambda b: ind.donchian(b, 20)["upper"],
        "donchian_lower": lambda b: ind.donchian(b, 20)["lower"],
    }
    return registry


REGISTRY = _build_registry()


@mcp.tool(name="trademcp_get_technical_indicators", annotations=tool_annotations("Technical indicators"))
async def trademcp_get_technical_indicators(
    symbol: Annotated[str, _fmt_field("NSE symbol or company name, e.g. 'RELIANCE'")],
    indicators: Annotated[
        list[str] | None,
        _fmt_field("Indicator names to compute, e.g. ['rsi_14','macd','atr_14']. Omit for all 57."),
    ] = None,
    range: Annotated[str, _fmt_field("Lookback window: 3mo, 6mo, 1y, 2y, 5y")] = "1y",
    interval: Annotated[str, _fmt_field("Bar size: 1d, 1wk, 1h, 30m")] = "1d",
    limit: Annotated[int, _fmt_field("How many recent data points to keep per indicator (1-100)")] = 5,
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Compute technical indicators for an Indian stock.

    Covers 57 indicators across trend (moving averages, MACD, ADX, Supertrend,
    Ichimoku, Parabolic SAR, Aroon, Vortex), momentum (RSI, Stochastic, CCI,
    Williams %R, MFI, ROC, CMO, TSI, Ultimate Oscillator), volatility (ATR,
    Bollinger, Keltner, Donchian, historical volatility), volume (OBV, VWAP,
    Chaikin Money Flow, Accumulation/Distribution, Force Index) and statistics.

    Args:
        symbol: NSE symbol or company name
        indicators: names to compute; omit for the full set
        range: lookback window
        interval: candle size
        limit: recent points kept per indicator
        response_format: 'markdown' or 'json'

    Returns:
        Markdown table (indicator, latest value, recent values) or JSON with
        'indicators' and 'series'.
    """
    try:
        resolved = await resolve(symbol)
    except (SymbolNotFound, DataSourceError) as exc:
        return error_text(exc)

    wanted = [name.strip().lower() for name in indicators] if indicators else list(REGISTRY)
    unknown = [name for name in wanted if name not in REGISTRY]
    wanted = [name for name in wanted if name in REGISTRY]

    try:
        bars, meta = await yahoo.get_bars(resolved.yahoo_ticker, range_=range, interval=interval)
    except DataSourceError as exc:
        return error_text(exc)

    if not bars:
        return error_text(DataSourceError(f"No price history available for '{symbol}'."))

    dates = [b.date for b in bars]
    summary: list[dict[str, Any]] = []
    series_out: dict[str, Any] = {}

    for name in wanted:
        values = REGISTRY[name](bars)
        defined = [(d, v) for d, v in zip(dates, values) if v is not None]
        if not defined:
            continue
        latest_date, latest_value = defined[-1]
        recent = defined[-limit:]
        series_out[name] = {"latest": latest_value, "date": latest_date,
                            "points": [{"date": d, "value": v} for d, v in recent]}
        summary.append(
            {
                "indicator": name,
                "latest": round(latest_value, 4) if isinstance(latest_value, float) else latest_value,
                "as_of": latest_date,
                "recent_values": ", ".join(f"{v:.2f}" for _, v in recent),
            }
        )

    payload = {
        "symbol": resolved.symbol,
        "name": resolved.name,
        "ticker": resolved.yahoo_ticker,
        "range": range,
        "interval": interval,
        "candles_used": len(bars),
        "indicator_count": len(summary),
        "indicators": summary,
        "series": series_out,
    }
    if unknown:
        payload["unknown_indicators"] = unknown
    return render(payload, response_format, f"{resolved.symbol} technical indicators")


@mcp.tool(name="trademcp_get_technical_analysis", annotations=tool_annotations("Technical analysis"))
async def trademcp_get_technical_analysis(
    symbol: Annotated[str, _fmt_field("NSE symbol or company name, e.g. 'INFY'")],
    range: Annotated[str, _fmt_field("Lookback window: 6mo, 1y, 2y, 5y")] = "1y",
    benchmark: Annotated[
        str,
        _fmt_field("Benchmark index for beta/relative strength: 'NIFTY 50' or 'SENSEX'"),
    ] = "NIFTY 50",
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Run a full technical analysis and produce a directional read on a stock.

    Scores every indicator, explains each signal in plain language, reports
    the composite score (Strong Buy / Buy / Neutral / Sell / Strong Sell), and
    adds risk statistics (annualised volatility, Sharpe, Sortino, max drawdown,
    beta, alpha, 30-day relative strength) plus recent candlestick patterns.

    Args:
        symbol: NSE symbol or company name
        range: lookback window for the analysis
        benchmark: benchmark index for beta and relative strength
        response_format: 'markdown' or 'json'

    Returns:
        Markdown or JSON with 'summary', 'signals', 'indicators', 'statistics'
        and 'candles'.
    """
    try:
        resolved = await resolve(symbol)
    except (SymbolNotFound, DataSourceError) as exc:
        return error_text(exc)

    try:
        bars, _ = await yahoo.get_bars(resolved.yahoo_ticker, range_=range, interval="1d")
    except DataSourceError as exc:
        return error_text(exc)

    if len(bars) < 30:
        return error_text(DataSourceError(f"Need at least 30 candles for analysis, got {len(bars)}."))

    benchmark_bars: list[Any] = []
    benchmark_name = benchmark.upper()
    if benchmark_name in ("NIFTY 50", "NIFTY50", "NIFTY", "SENSEX"):
        from ..symbols import INDEX_TICKERS

        ticker = INDEX_TICKERS.get(benchmark_name if benchmark_name in INDEX_TICKERS else "NIFTY 50")
        if ticker:
            try:
                benchmark_bars, _ = await yahoo.get_bars(ticker, range_=range, interval="1d")
            except DataSourceError:
                benchmark_bars = []

    analysis = sg.technical_signals(bars, benchmark_bars or None)
    payload = {
        "symbol": resolved.symbol,
        "name": resolved.name,
        "ticker": resolved.yahoo_ticker,
        "range": range,
        "last_close": bars[-1].close,
        "last_date": bars[-1].date,
        "summary": analysis["summary"],
        "signals": analysis["signals"],
        "indicators": analysis["indicators"],
        "statistics": analysis["statistics"],
        "candlestick_patterns": analysis["candles"],
    }
    return render(payload, response_format, f"{resolved.symbol} technical analysis")


@mcp.tool(name="trademcp_get_support_resistance", annotations=tool_annotations("Support and resistance"))
async def trademcp_get_support_resistance(
    symbol: Annotated[str, _fmt_field("NSE symbol or company name, e.g. 'TCS'")],
    range: Annotated[str, _fmt_field("Lookback window: 6mo, 1y, 2y, 5y")] = "1y",
    response_format: Annotated[ResponseFormat, _fmt_field("'markdown' or 'json'")] = ResponseFormat.MARKDOWN,
) -> str:
    """Compute support and resistance levels for an Indian stock.

    Returns pivot points in classic, Camarilla, Fibonacci, Woodie and DeMark
    styles, Fibonacci retracement levels over the recent range, recent swing
    highs and lows, 20-day Donchian channels, ATR and the position of the
    price inside its 52-week range.

    Args:
        symbol: NSE symbol or company name
        range: lookback window
        response_format: 'markdown' or 'json'

    Returns:
        Markdown or JSON with 'pivots', 'fibonacci_retracement', 'range', 'swing_highs' and 'swing_lows'.
    """
    try:
        resolved = await resolve(symbol)
    except (SymbolNotFound, DataSourceError) as exc:
        return error_text(exc)

    try:
        bars, _ = await yahoo.get_bars(resolved.yahoo_ticker, range_=range, interval="1d")
    except DataSourceError as exc:
        return error_text(exc)

    if len(bars) < 2:
        return error_text(DataSourceError("Not enough price history to compute levels."))

    levels = sg.support_resistance(bars)
    payload = {"symbol": resolved.symbol, "name": resolved.name, **levels}
    return render(payload, response_format, f"{resolved.symbol} support & resistance")
