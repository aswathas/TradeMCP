# TradeMCP — Live demo

Real output captured from the running server against live free data sources.
Captured 2026-10-21 02:00 IST.

**14/14 tool calls returned usable output.**

## `trademcp_search_symbol`

*Find a company by name, not ticker*

```json
{
  "query": "tata motors",
  "limit": 4
}
```

Took 0.03s.

```markdown
# Symbol search: tata motors

## Query

tata motors

## Match Count

2

## Matches

| Symbol | Name                                   | Series | Listed On   | Paid Up Value | Market Lot | Isin         | Face Value | Match | Score |
|--------|----------------------------------------|--------|-------------|---------------|------------|--------------|------------|-------|-------|
| TMCV   | Tata Motors Limited                    | EQ     | 12-NOV-2025 | 2             | 1          | INE1TAE01010 | 2          | name  | 1.00  |
| TMPV   | Tata Motors Passenger Vehicles Limited | EQ     | 22-JUL-1998 | 2             | 1          | INE155A01022 | 2          | name  | 0.95  |
```

## `trademcp_get_quote`

*Live quote plus valuation and returns*

```json
{
  "symbol": "RELIANCE"
}
```

Took 2.59s.

```markdown
# RELIANCE - Reliance Industries Limited

## Symbol

RELIANCE

## Name

Reliance Industries Limited

## Exchange

NSE

## Ticker

RELIANCE.NS

## Industry

Oil Gas & Consumable Fuels

## Isin

INE002A01018

## Currency

INR

## Last Traded At

2026-10-19 09:59 UTC

## Price

1,202.00

## Change

-9.20

## Change Pct

-0.76

## Open

1,212.00

## Day High

1,228.20

## Day Low

1,201.00

## Previous Close

-

## Volume

1.56 Cr

## Average Volume

1.45 Cr

## Week 52 High

1,611.80

## Week 52 Low

1,152.20

## Position In 52W Range Pct

10.84

## Market Cap

1,626,603.21 Cr

## Trailing Pe

21.77

## Forward Pe

16.92

## Price To Book

1.80

## Eps Ttm

55.22

## Book Value

668.04

## Dividend Yield Pct

0.50

## Beta

-

## Returns

| Metric      | Value  |
|-------------|--------|
| 1 Week Pct  | 3.72   |
| 1 Month Pct | -3.37  |
| 3 Month Pct | -9.15  |
| 6 Month Pct | -11.94 |
| 1 Year Pct  | -      |
```

## `trademcp_get_price_history`

*Raw OHLCV candles*

```json
{
  "symbol": "INFY",
  "range": "1mo",
  "limit": 6
}
```

Took 0.16s.

```markdown
# INFY price history (1mo, 1d)

## Symbol

INFY

## Name

Infosys Limited

## Ticker

INFY.NS

## Range

1mo

## Interval

1d

## Currency

INR

## Exchange

NSI

## Period Summary

| Metric            | Value      |
|-------------------|------------|
| Candles Available | 20         |
| From              | 2026-09-21 |
| To                | 2026-10-19 |
| Start Close       | 1,038.50   |
| End Close         | 1,130.70   |
| Period Return Pct | 8.88       |
| Highest           | 1,167.85   |
| Lowest            | 980.40     |
| Total Volume      | 25.19 Cr   |

## Candles

| Date       | Open     | High     | Low      | Close    | Volume  | Adj Close |
|------------|----------|----------|----------|----------|---------|-----------|
| 2026-10-19 | 1,156.95 | 1,156.95 | 1,125.10 | 1,130.70 | 1.33 Cr | 1,130.70  |
| 2026-10-16 | 1,127.50 | 1,167.85 | 1,122.00 | 1,161.20 | 2.56 Cr | 1,161.20  |
| 2026-10-15 | 1,099.00 | 1,126.70 | 1,095.80 | 1,110.00 | 1.60 Cr | 1,110.00  |
| 2026-10-14 | 1,073.70 | 1,096.40 | 1,069.45 | 1,088.00 | 2.21 Cr | 1,088.00  |
| 2026-10-13 | 1,029.20 | 1,065.00 | 1,027.00 | 1,062.10 | 2.18 Cr | 1,062.10  |
| 2026-10-12 | 1,029.30 | 1,033.80 | 1,010.65 | 1,020.00 | 84.29 L | 1,020.00  |
```

## `trademcp_get_index_snapshot`

*Where the market stands*

```json
{
  "indices": [
    "NIFTY 50",
    "SENSEX",
    "NIFTY BANK",
    "INDIA VIX"
  ]
}
```

Took 1.14s.

```markdown
# Indian market index snapshot

## Index Count

4

## Indices

| Index      | Price     | Change  | Change Pct | Day High  | Day Low   | Previous Close | Volume |
|------------|-----------|---------|------------|-----------|-----------|----------------|--------|
| NIFTY 50   | 22,888.95 | -257.20 | -1.11      | 23,175.25 | 22,845.00 | -              | 0      |
| SENSEX     | 73,852.90 | -876.38 | -1.17      | 74,849.75 | 73,708.54 | -              | 0      |
| NIFTY BANK | 55,488.10 | -355.90 | -0.64      | 55,883.70 | 55,331.10 | -              | 0      |
| INDIA VIX  | 14.77     | 0.75    | 5.33       | 14.97     | 13.32     | -              | 0      |
```

## `trademcp_get_market_breadth`

*Breadth across index constituents*

```json
{
  "index": "NIFTY 50",
  "include_trend": false
}
```

Took 2.13s.

```markdown
# Market breadth - NIFTY 50

## Index

NIFTY 50

## Constituents Fetched

50

## Breadth

| Metric                | Value |
|-----------------------|-------|
| Advancers             | 9     |
| Decliners             | 41    |
| Unchanged             | 0     |
| Advance Decline Ratio | 0.22  |
| Advance Pct           | 18.00 |
| Decline Pct           | 82.00 |
| Average Change Pct    | -0.92 |
| Median Change Pct     | -1.02 |
| Above 200Dma Pct      | -     |

## Top Gainers

| Symbol    | Change Pct | Price    |
|-----------|------------|----------|
| JSWSTEEL  | 2.06       | 1,241.30 |
| ONGC      | 1.35       | 225.00   |
| SBIN      | 1.15       | 973.70   |
| LT        | 0.96       | 3,661.90 |
| EICHERMOT | 0.89       | 7,349.00 |

## Top Losers

| Symbol     | Change Pct | Price    |
|------------|------------|----------|
| AXISBANK   | -4.19      | 1,236.00 |
| TMPV       | -3.09      | 278.00   |
| INFY       | -2.63      | 1,130.70 |
| BAJFINANCE | -2.52      | 957.35   |
| APOLLOHOSP | -2.41      | 7,700.00 |
```

## `trademcp_compare_stocks`

*Side-by-side on price, quality and momentum*

```json
{
  "symbols": [
    "RELIANCE",
    "TCS"
  ]
}
```

Took 1.01s.

```markdown
# Stock comparison

## Compared

2

## Stocks

| Symbol   | Name                              | Industry                   | Price    | Change Pct | Market Cap      | Pe Ratio | Price To Book | Eps    | Dividend Yield Pct | Week 52 High | Week 52 Low | Volume  | Roe Pct | Net Margin Pct | Debt To Equity | Revenue Cagr 3Y Pct | Health Score | Technical Score | Technical Label |
|----------|-----------------------------------|----------------------------|----------|------------|-----------------|----------|---------------|--------|--------------------|--------------|-------------|---------|---------|----------------|----------------|---------------------|--------------|-----------------|-----------------|
| RELIANCE | Reliance Industries Limited       | Oil Gas & Consumable Fuels | 1,202.00 | -0.76      | 1,626,603.21 Cr | 21.77    | 1.80          | 55.22  | 0.50               | 1,611.80     | 1,152.20    | 1.56 Cr | 8.93    | 7.64           | 0.44           | 6.39                | 62.10        | -2.70           | Neutral         |
| TCS      | Tata Consultancy Services Limited | Information Technology     | 2,460.90 | -0.17      | 890,375.14 Cr   | 17.25    | 7.48          | 142.66 | 1.95               | 3,350.00     | 1,976.80    | 86.75 L | 45.89   | 18.43          | 0.11           | 5.80                | 73.30        | 31.70           | Buy             |
```

## `trademcp_get_technical_indicators`

*Any of the 57 indicators*

```json
{
  "symbol": "RELIANCE",
  "indicators": [
    "rsi_14",
    "macd",
    "atr_14",
    "supertrend"
  ],
  "limit": 3
}
```

Took 0.01s.

```markdown
# RELIANCE technical indicators

## Symbol

RELIANCE

## Name

Reliance Industries Limited

## Ticker

RELIANCE.NS

## Range

1y

## Interval

1d

## Candles Used

247

## Indicator Count

4

## Indicators

| Indicator  | Latest   | As Of      | Recent Values             |
|------------|----------|------------|---------------------------|
| rsi_14     | 46.58    | 2026-10-19 | 49.64, 48.75, 46.58       |
| macd       | -17.86   | 2026-10-19 | -23.17, -19.91, -17.86    |
| atr_14     | 24.29    | 2026-10-19 | 24.19, 24.06, 24.29       |
| supertrend | 1,146.87 | 2026-10-19 | 1146.87, 1228.86, 1146.87 |

## Series

### Rsi 14

### Latest

46.58

### Date

2026-10-19

### Points

| Date       | Value |
|------------|-------|
| 2026-10-15 | 49.64 |
| 2026-10-16 | 48.75 |
| 2026-10-19 | 46.58 |


### Macd

### Latest

-17.86

### Date

2026-10-19

### Points

| Date       | Value  |
|------------|--------|
| 2026-10-15 | -23.17 |
| 2026-10-16 | -19.91 |
| 2026-10-19 | -17.86 |


### Atr 14

### Latest

24.29

### Date

2026-10-19

### Points

| Date       | Value |
|------------|-------|
| 2026-10-15 | 24.19 |
| 2026-10-16 | 24.06 |
| 2026-10-19 | 24.29 |


### Supertrend

### Latest

1,146.87

### Date

2026-10-19

### Points

| Date       | Value    |
|------------|----------|
| 2026-10-15 | 1,146.87 |
| 2026-10-16 | 1,228.86 |
| 2026-10-19 | 1,146.87 |
```

## `trademcp_get_technical_analysis`

*Scored signals plus risk statistics*

```json
{
  "symbol": "HDFCBANK",
  "range": "1y"
}
```

Took 0.53s.

```markdown
# HDFCBANK technical analysis

## Symbol

HDFCBANK

## Name

HDFC Bank Limited

## Ticker

HDFCBANK.NS

## Range

1y

## Last Close

712.00

## Last Date

2026-10-19

## Summary

| Metric        | Value   |
|---------------|---------|
| Score         | -5.70   |
| Label         | Neutral |
| Bullish       | 7       |
| Bearish       | 9       |
| Neutral       | 4       |
| Total Signals | 20      |

## Signals

| Indicator             | Value    | Signal  | Strength | Note                                          |
|-----------------------|----------|---------|----------|-----------------------------------------------|
| SMA alignment         | 712.00   | bearish | 3        | Price < 50 SMA < 200 SMA - clean downtrend    |
| SMA 20/50 crossover   | 718.37   | bullish | 2        | 20 SMA above 50 SMA                           |
| EMA 20/50             | 715.65   | bearish | 2        | Short-term EMA above/below the long-term EMA  |
| Supertrend            | 686.78   | bullish | 3        | Supertrend is above price                     |
| Parabolic SAR         | 693.00   | bullish | 2        | Price trading above/below the SAR stop        |
| Ichimoku cross        | 712.70   | bearish | 2        | Tenkan-sen above/below Kijun-sen              |
| Ichimoku cloud        | 712.00   | bearish | 2        | Price above/below/inside the Kumo cloud       |
| ADX / DMI             | 14.64    | neutral | 1        | ADX 14.6 (weak trend), +DI 23.3 vs -DI 20.9   |
| RSI (14)              | 47.92    | bearish | 1        | RSI 47.9 is below the midline                 |
| MACD (12,26,9)        | 1.36     | bullish | 3        | MACD -1.49 above signal -2.85                 |
| Stochastic %K         | 48.42    | bearish | 1        | %K vs %D crossover                            |
| CCI (20)              | -8.03    | bearish | 2        | Below zero - sellers in control               |
| ROC (10)              | 1.02     | bullish | 2        | 10-day rate of change +1.0%                   |
| Ultimate Oscillator   | 51.14    | bullish | 2        | UO at 51.1                                    |
| Awesome Oscillator    | 3.68     | bullish | 1        | 5/34 median price spread                      |
| Bollinger %B          | 0.38     | neutral | 1        | Inside the bands                              |
| VWAP                  | 818.55   | bearish | 2        | Price above/below the volume-weighted average |
| ATR (14)              | 15.10    | neutral | 0        | Daily range ~15.10 (2.1% of price)            |
| Volume vs 20d average | 1.09     | neutral | 1        | Volume running at 1.09x its 20-day average    |
| OBV (21d change)      | -8.22 Cr | bearish | 2        | Distribution                                  |

## Indicators

| Metric               | Value   |
|----------------------|---------|
| Price                | 712.00  |
| Sma 20               | 718.36  |
| Sma 50               | 718.07  |
| Sma 200              | 801.18  |
| Ema 20               | 715.65  |
| Ema 50               | 724.33  |
| Rsi 14               | 47.92   |
| Macd                 | -1.49   |
| Macd Signal          | -2.85   |
| Macd Histogram       | 1.36    |
| Adx 14               | 14.64   |
| Plus Di              | 23.32   |
| Minus Di             | 20.89   |
| Supertrend           | 686.78  |
| Supertrend Direction | bullish |
| Parabolic Sar        | 693.00  |
| Bollinger Upper      | 744.84  |
| Bollinger Middle     | 718.36  |
| Bollinger Lower      | 691.89  |
| Bollinger Percent B  | 0.38    |
| Stochastic K         | 48.42   |
| Stochastic D         | 69.58   |
| Cci 20               | -8.03   |
| Williams R           | -51.58  |
| Money Flow Index     | 41.03   |
| Roc 10               | 1.02    |
| Ultimate Oscillator  | 51.14   |
| Awesome Oscillator   | 3.68    |
| Vwap                 | 818.55  |
| Atr 14               | 15.10   |
| Volume Ratio 20      | 1.09    |
| Ichimoku Tenkan      | 712.70  |
| Ichimoku Kijun       | 715.60  |

## Statistics

| Metric                    | Value  |
|---------------------------|--------|
| Annualised Volatility Pct | 22.28  |
| Sharpe Ratio              | -1.46  |
| Sortino Ratio             | -1.46  |
| Max Drawdown Pct          | -31.94 |
| Beta                      | 1.18   |
| Annualised Alpha Pct      | -0.20  |
| Return 30D Pct            | -0.01  |
| Benchmark Return 30D Pct  | -4.22  |
| Relative Strength 30D Pct | 4.21   |

## Candlestick Patterns

| Pattern           | Date       | Bias    | Note                                         |
|-------------------|------------|---------|----------------------------------------------|
| Piercing Line     | 2026-10-09 | bullish | Bulls recovered over half the prior loss     |
| Piercing Line     | 2026-10-13 | bullish | Bulls recovered over half the prior loss     |
| Doji              | 2026-10-16 | neutral | Indecision - open and close nearly equal     |
| Bearish Engulfing | 2026-10-19 | bearish | Sellers wiped out the prior session's buyers |
| Evening Star      | 2026-10-19 | bearish | Up day, indecision, then a strong down day   |
```

## `trademcp_get_support_resistance`

*Five pivot styles, fib levels, swing points*

```json
{
  "symbol": "SBIN"
}
```

Took 0.75s.

```markdown
# SBIN support & resistance

## Symbol

SBIN

## Name

State Bank of India

## Price

973.70

## As Of

2026-10-19

## Pivots

### Classic

| Metric | Value  |
|--------|--------|
| Pivot  | 960.07 |
| R1     | 968.43 |
| R2     | 974.27 |
| R3     | 982.63 |
| S1     | 954.23 |
| S2     | 945.87 |
| S3     | 940.03 |

### Camarilla

| Metric | Value  |
|--------|--------|
| R1     | 963.90 |
| R2     | 965.20 |
| R3     | 966.50 |
| R4     | 970.41 |
| S1     | 961.30 |
| S2     | 960.00 |
| S3     | 958.69 |
| S4     | 954.79 |

### Fibonacci

| Metric | Value  |
|--------|--------|
| Pivot  | 960.07 |
| R1     | 965.49 |
| R2     | 968.84 |
| R3     | 974.27 |
| S1     | 954.64 |
| S2     | 951.29 |
| S3     | 945.87 |

### Woodie

| Metric | Value  |
|--------|--------|
| Pivot  | 960.70 |
| R1     | 969.70 |
| R2     | 974.90 |
| S1     | 955.50 |
| S2     | 946.50 |

### Demark

| Metric | Value  |
|--------|--------|
| R1     | 961.53 |
| S1     | 957.15 |
| S2     | 971.35 |


## Fibonacci Retracement

| Metric | Value    |
|--------|----------|
| 0.0%   | 1,234.70 |
| 23.6%  | 1,153.60 |
| 38.2%  | 1,103.43 |
| 50.0%  | 1,062.87 |
| 61.8%  | 1,022.32 |
| 78.6%  | 964.59   |
| 100.0% | 891.05   |

## Range

| Metric                | Value    |
|-----------------------|----------|
| Period High           | 1,234.70 |
| Period Low            | 891.05   |
| Period Days           | 247      |
| Position In Range Pct | 24.05    |

## Swing Highs

| Date       | Price    |
|------------|----------|
| 2026-04-08 | 1,077.80 |
| 2026-04-20 | 1,120.95 |
| 2026-05-07 | 1,108.00 |
| 2026-05-26 | 978.80   |
| 2026-06-18 | 1,045.70 |
| 2026-06-25 | 1,055.40 |
| 2026-07-02 | 1,059.80 |
| 2026-07-21 | 1,067.00 |
| 2026-08-07 | 1,124.50 |
| 2026-08-26 | 1,062.30 |

## Swing Lows

| Date       | Price    |
|------------|----------|
| 2026-05-18 | 933.90   |
| 2026-06-03 | 937.20   |
| 2026-06-24 | 1,020.50 |
| 2026-07-08 | 1,011.70 |
| 2026-07-14 | 1,011.40 |
| 2026-07-24 | 1,000.80 |
| 2026-07-30 | 1,007.60 |
| 2026-08-25 | 1,031.30 |
| 2026-09-15 | 968.00   |
| 2026-10-08 | 937.50   |

## Donchian 20

### Upper

- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- 976.70
- 984.45
- 986.60
- 986.60
- 986.60
- 988.95
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 999.00
- 991.20
- 991.20
- 991.20
- 983.00
- 985.65
- 987.65
- 1,009.50
- 1,015.50
- 1,024.00
- 1,024.00
- 1,024.00
- 1,024.00
- 1,024.00
- 1,029.50
- 1,030.40
- 1,030.40
- 1,047.45
- 1,047.45
- 1,052.00
- 1,052.00
- 1,055.50
- 1,055.50
- 1,055.50
- 1,065.60
- 1,075.00
- 1,082.50
- 1,082.50
- 1,089.80
- 1,089.80
- 1,089.80
- 1,089.80
- 1,150.00
- 1,154.00
- 1,187.50
- 1,203.70
- 1,203.70
- 1,212.30
- 1,225.50
- 1,225.50
- 1,225.50
- 1,225.50
- 1,231.10
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,234.70
- 1,228.10
- 1,215.40
- 1,211.80
- 1,197.30
- 1,183.20
- 1,183.20
- 1,169.30
- 1,119.90
- 1,119.90
- 1,115.90
- 1,098.00
- 1,088.00
- 1,088.00
- 1,088.00
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,120.95
- 1,117.85
- 1,117.85
- 1,114.80
- 1,114.80
- 1,114.80
- 1,110.50
- 1,108.00
- 1,108.00
- 1,108.00
- 1,108.00
- 1,108.00
- 1,108.00
- 1,095.00
- 1,007.00
- 1,009.00
- 1,012.40
- 1,012.40
- 1,018.70
- 1,034.00
- 1,034.00
- 1,034.00
- 1,045.70
- 1,045.70
- 1,045.70
- 1,045.70
- 1,045.70
- 1,055.40
- 1,055.40
- 1,055.40
- 1,055.40
- 1,059.80
- 1,059.80
- 1,059.80
- 1,059.80
- 1,059.80
- 1,059.80
- 1,059.80
- 1,059.80
- 1,059.80
- 1,059.80
- 1,059.80
- 1,059.80
- 1,065.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,067.00
- 1,088.10
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,124.50
- 1,113.30
- 1,086.80
- 1,086.80
- 1,086.80
- 1,082.00
- 1,068.80
- 1,067.70
- 1,062.30
- 1,062.30
- 1,062.30
- 1,062.30
- 1,062.30
- 1,062.30
- 1,060.00
- 1,060.00
- 1,060.00
- 1,051.30
- 1,036.00
- 1,036.00
- 1,029.20
- 1,021.70
- 1,012.20
- 1,012.20
- 1,011.90
- 1,001.90
- 1,000.90
- 1,000.90
- 1,000.90
- 1,000.10
- 1,000.10

### Lower

- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- -
- 891.05
- 900.95
- 900.95
- 900.95
- 906.00
- 917.70
- 930.25
- 930.25
- 930.25
- 937.50
- 941.50
- 944.00
- 944.00
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 944.45
- 946.70
- 950.45
- 950.45
- 955.25
- 957.25
- 957.25
- 957.25
- 958.05
- 959.50
- 959.50
- 959.50
- 959.50
- 959.50
- 959.50
- 959.50
- 959.50
- 959.50
- 973.50
- 980.35
- 983.95
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 990.00
- 1,040.30
- 1,051.00
- 1,051.00
- 1,051.00
- 1,064.30
- 1,064.30
- 1,064.30
- 1,064.30
- 1,042.30
- 1,036.10
- 1,036.10
- 1,036.10
- 1,036.10
- 1,036.10
- 1,014.20
- 1,014.20
- 1,014.20
- 1,013.00
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 975.80
- 977.90
- 977.90
- 1,005.05
- 1,012.00
- 1,030.00
- 1,010.90
- 971.10
- 962.40
- 961.20
- 961.20
- 957.00
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 933.90
- 935.00
- 935.00
- 937.20
- 937.20
- 937.20
- 937.20
- 937.20
- 937.20
- 937.20
- 937.20
- 937.20
- 961.10
- 965.15
- 965.15
- 983.00
- 993.00
- 993.00
- 1,004.35
- 1,007.40
- 1,007.40
- 1,011.40
- 1,011.40
- 1,011.40
- 1,011.40
- 1,011.40
- 1,011.40
- 1,006.50
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,000.80
- 1,007.60
- 1,007.60
- 1,007.60
- 1,007.60
- 1,023.50
- 1,030.90
- 1,030.90
- 1,027.10
- 1,017.30
- 1,017.30
- 1,016.10
- 1,000.60
- 1,000.60
- 992.40
- 992.40
- 992.40
- 968.00
- 968.00
- 968.00
- 968.00
- 968.00
- 968.00
- 968.00
- 968.00
- 968.00
- 956.10
- 953.00
- 953.00
- 945.80
- 945.80
- 945.80
- 945.60
- 937.50
- 937.50
- 937.50
- 937.50
- 937.50
- 937.50
- 937.50
- 937.50


## Volatility

| Metric              | Value |
|---------------------|-------|
| Atr 14              | 17.40 |
| Bollinger Width Pct | 6.28  |
```

## `trademcp_get_fundamentals`

*The full fundamental picture*

```json
{
  "symbol": "TCS"
}
```

Took 0.88s.

```markdown
# TCS fundamentals

## Symbol

TCS

## As Of

| Metric   | Value      |
|----------|------------|
| Annual   | 2026-03-31 |
| Trailing | 2026-09-23 |
| Price    | 2,460.90   |

## Valuation

| Metric               | Value         |
|----------------------|---------------|
| Market Cap           | 756,035.57 Cr |
| Enterprise Value     | 767,318.57 Cr |
| Pe Ratio             | 15.18         |
| Peg Ratio            | 2.73          |
| Price To Book        | 7.05          |
| Price To Sales       | 2.83          |
| Ev To Ebitda         | 9.92          |
| Ev To Sales          | 2.87          |
| Dividend Yield Pct   | 2.60          |
| Book Value Per Share | 296.40        |
| Eps Ttm              | 136.01        |
| Dividend Per Share   | -             |

## Profitability

| Metric                 | Value |
|------------------------|-------|
| Gross Margin Pct       | 45.10 |
| Operating Margin Pct   | 25.10 |
| Ebitda Margin Pct      | 27.07 |
| Net Margin Pct         | 18.43 |
| Return On Equity Pct   | 45.89 |
| Return On Assets Pct   | 26.98 |
| Roce Pct               | 62.21 |
| Roic Pct               | 56.29 |
| Asset Turnover         | 1.46  |
| Equity Multiplier      | 1.70  |
| Effective Tax Rate Pct | 24.86 |

## Leverage

| Metric               | Value       |
|----------------------|-------------|
| Debt To Equity       | 0.11        |
| Debt To Assets       | 6.19        |
| Cash And Equivalents | 6,405.00 Cr |
| Net Debt             | 4,878.00 Cr |
| Net Debt To Ebitda   | 0.07        |
| Interest Coverage    | 54.62       |
| Debt To Capital Pct  | 9.52        |

## Liquidity

| Metric                    | Value        |
|---------------------------|--------------|
| Current Ratio             | 2.23         |
| Quick Ratio               | 2.23         |
| Cash Ratio                | 0.11         |
| Working Capital           | 74,791.00 Cr |
| Working Capital Per Share | 206.71       |
| Operating Cash Flow       | 52,094.00 Cr |
| Free Cash Flow            | 47,948.00 Cr |
| Fcf Margin Pct            | 17.96        |
| Cfo To Net Income         | 1.06         |
| Capex                     | -4,146.00 Cr |
| Cash Flow Per Share       | 143.98       |
| Fcf Per Share             | 132.52       |

## Growth

| Metric                      | Value |
|-----------------------------|-------|
| Revenue Yoy Pct             | 4.58  |
| Net Income Yoy Pct          | 1.35  |
| Eps Yoy Pct                 | 1.36  |
| Operating Cash Flow Yoy Pct | 6.51  |
| Revenue Cagr 3Y Pct         | 5.80  |
| Revenue Cagr 5Y Pct         | -     |
| Net Income Cagr 3Y Pct      | 5.30  |
| Net Income Cagr 5Y Pct      | -     |

## Dupont

| Metric              | Value |
|---------------------|-------|
| Net Margin Pct      | 18.43 |
| Asset Turnover      | 1.46  |
| Equity Multiplier   | 1.70  |
| Roe From Dupont Pct | 45.89 |

## India Specific

### Roce Pct

63.00

### Roe Pct

51.80

### Book Value

329.00

### Face Value

1.00

### Market Cap Crore

890,375.00

### Debt To Equity

-

### Roce History

| Metric   | Value |
|----------|-------|
| Mar 2015 | 50.00 |
| Mar 2016 | 51.00 |
| Mar 2017 | 44.00 |
| Mar 2018 | 39.00 |
| Mar 2019 | 47.00 |
| Mar 2020 | 47.00 |
| Mar 2021 | 49.00 |
| Mar 2022 | 54.00 |
| Mar 2023 | 59.00 |
| Mar 2024 | 64.00 |
| Mar 2025 | 65.00 |
| Mar 2026 | 63.00 |

### Roce Period

Mar 2026

### Debtor Days

93.00

### Inventory Days

-

### Days Payable

-

### Cash Conversion Cycle

93.00

### Shareholding

### Periods

- Dec 2023
- Mar 2024
- Jun 2024
- Sep 2024
- Dec 2024
- Mar 2025
- Jun 2025
- Sep 2025
- Dec 2025
- Mar 2026
- Jun 2026
- Sep 2026

### Promoters +

- 72.41
- 71.77
- 71.77
- 71.77
- 71.77
- 71.77
- 71.77
- 71.77
- 71.77
- 71.77
- 71.77
- 71.77

### Fiis +

- 12.46
- 12.70
- 12.35
- 12.66
- 12.68
- 12.04
- 11.48
- 10.33
- 10.37
- 9.66
- 9.07
- 9.01

### Diis +

- 10.03
- 10.61
- 11.00
- 10.86
- 10.86
- 11.49
- 11.95
- 12.64
- 12.81
- 13.34
- 13.41
- 13.57

### Government +

- 0.05
- 0.06
- 0.06
- 0.06
- 0.06
- 0.06
- 0.06
- 0.06
- 0.06
- 0.06
- 0.06
- 0.00

### Public +

- 5.03
- 4.86
- 4.82
- 4.66
- 4.63
- 4.63
- 4.77
- 5.21
- 4.98
- 5.16
- 5.69
- 5.66

### No. Of Shareholders

- 23.36 L
- 22.03 L
- 21.81 L
- 20.94 L
- 20.75 L
- 21.15 L
- 21.64 L
- 23.88 L
- 23.32 L
- 24.50 L
- 26.05 L
- 25.79 L



## Health Score

### Score

94.30

### Label

Strong

### Components

| Metric                 | Value | Score | Weight |
|------------------------|-------|-------|--------|
| return_on_equity_pct   | 45.89 | 15    | 15     |
| roce_pct               | 62.21 | 15    | 15     |
| net_margin_pct         | 18.43 | 10    | 10     |
| operating_margin_pct   | 25.10 | 8     | 8      |
| debt_to_equity         | 0.11  | 12    | 12     |
| interest_coverage      | 54.62 | 8     | 8      |
| current_ratio          | 2.23  | 8     | 8      |
| revenue_cagr_3y_pct    | 5.80  | 8.70  | 12     |
| net_income_cagr_3y_pct | 5.30  | 4.64  | 7      |
| fcf_margin_pct         | 17.96 | 5     | 5      |


## Raw Series

### Revenue

- ('2023-03-31', 2254580000000.0)
- ('2024-03-31', 2408930000000.0)
- ('2025-03-31', 2553240000000.0)
- ('2026-03-31', 2670210000000.0)

### Net Income

- ('2023-03-31', 421470000000.0)
- ('2024-03-31', 459080000000.0)
- ('2025-03-31', 485530000000.0)
- ('2026-03-31', 492100000000.0)

### Eps

- ('2023-03-31', 115.19)
- ('2024-03-31', 125.88)
- ('2025-03-31', 134.19)
- ('2026-03-31', 136.01)


## Name

Tata Consultancy Services Limited

## Ticker

TCS.NS

## Industry

Information Technology

## Isin

INE467B01029

## Market

| Metric       | Value         |
|--------------|---------------|
| Price        | 2,460.90      |
| Change Pct   | -0.17         |
| Market Cap   | 890,375.14 Cr |
| 52 Week High | 3,350.00      |
| 52 Week Low  | 1,976.80      |
| Volume       | 86.75 L       |
```

## `trademcp_get_valuation`

*Valuation sheet with a plain-English read*

```json
{
  "symbol": "INFY"
}
```

Took 2.38s.

```markdown
# INFY valuation

## Symbol

INFY

## Name

Infosys Limited

## Industry

Information Technology

## Price

1,130.70

## Valuation

| Metric               | Value         |
|----------------------|---------------|
| Market Cap           | 413,337.56 Cr |
| Enterprise Value     | 413,434.26 Cr |
| Pe Ratio             | 13.16         |
| Peg Ratio            | 1.80          |
| Price To Book        | 422.38        |
| Price To Sales       | 205.05        |
| Ev To Ebitda         | 7.98          |
| Ev To Sales          | 205.10        |
| Dividend Yield Pct   | 4.25          |
| Book Value Per Share | 2.38          |
| Eps Ttm              | 0.80          |
| Dividend Per Share   | -             |

## Growth Context

| Metric                 | Value |
|------------------------|-------|
| Revenue Cagr 3Y Pct    | 3.44  |
| Net Income Cagr 3Y Pct | 3.58  |
| Return On Equity Pct   | 33.85 |
| Net Margin Pct         | 16.44 |

## Verdict

- P/E of 13.2 sits below the usual large-cap Indian band (15-30).
- 3-year revenue CAGR is 3.4%.
- ROE is 33.9% - healthy for a listed company.
- Debt/equity is 0.10 - conservative.
```

## `trademcp_get_financial_statements`

*Income statement, balance sheet, cash flow*

```json
{
  "symbol": "RELIANCE",
  "years": 3
}
```

Took 0.57s.

```markdown
# RELIANCE financial statements (annual)

## Symbol

RELIANCE

## Name

Reliance Industries Limited

## Period Type

annual

## Periods

- 2024-03-31
- 2025-03-31
- 2026-03-31

## Income Statement

### Revenue

| Metric     | Value           |
|------------|-----------------|
| 2024-03-31 | 901,064.00 Cr   |
| 2025-03-31 | 964,693.00 Cr   |
| 2026-03-31 | 1,057,219.00 Cr |

### Gross Profit

| Metric     | Value         |
|------------|---------------|
| 2024-03-31 | 226,465.00 Cr |
| 2025-03-31 | 242,006.00 Cr |
| 2026-03-31 | 270,395.00 Cr |

### Operating Income

| Metric     | Value         |
|------------|---------------|
| 2024-03-31 | 111,666.00 Cr |
| 2025-03-31 | 112,462.00 Cr |
| 2026-03-31 | 121,377.00 Cr |

### Ebitda

| Metric     | Value         |
|------------|---------------|
| 2024-03-31 | 176,944.00 Cr |
| 2025-03-31 | 181,274.00 Cr |
| 2026-03-31 | 204,906.00 Cr |

### Net Income

| Metric     | Value        |
|------------|--------------|
| 2024-03-31 | 69,621.00 Cr |
| 2025-03-31 | 69,648.00 Cr |
| 2026-03-31 | 80,775.00 Cr |

### Eps Diluted

| Metric     | Value |
|------------|-------|
| 2024-03-31 | 51.45 |
| 2025-03-31 | 51.47 |
| 2026-03-31 | 59.69 |


## Balance Sheet

### Total Assets

| Metric     | Value           |
|------------|-----------------|
| 2024-03-31 | 1,755,986.00 Cr |
| 2025-03-31 | 1,950,121.00 Cr |
| 2026-03-31 | 2,178,140.00 Cr |

### Total Debt

| Metric     | Value         |
|------------|---------------|
| 2024-03-31 | 346,142.00 Cr |
| 2025-03-31 | 369,575.00 Cr |
| 2026-03-31 | 398,000.00 Cr |

### Shareholders Equity

| Metric     | Value         |
|------------|---------------|
| 2024-03-31 | 793,481.00 Cr |
| 2025-03-31 | 843,200.00 Cr |
| 2026-03-31 | 904,030.00 Cr |

### Working Capital

| Metric     | Value        |
|------------|--------------|
| 2024-03-31 | 72,733.00 Cr |
| 2025-03-31 | 45,533.00 Cr |
| 2026-03-31 | 52,995.00 Cr |

### Invested Capital

| Metric     | Value           |
|------------|-----------------|
| 2024-03-31 | 1,118,103.00 Cr |
| 2025-03-31 | 1,190,730.00 Cr |
| 2026-03-31 | 1,278,451.00 Cr |


## Cash Flow

### Operating Cash Flow

| Metric     | Value         |
|------------|---------------|
| 2024-03-31 | 158,788.00 Cr |
| 2025-03-31 | 178,703.00 Cr |
| 2026-03-31 | 192,113.00 Cr |

### Free Cash Flow

| Metric     | Value        |
|------------|--------------|
| 2024-03-31 | 5,905.00 Cr  |
| 2025-03-31 | 38,736.00 Cr |
| 2026-03-31 | 69,197.00 Cr |

### Capital Expenditure

| Metric     | Value          |
|------------|----------------|
| 2024-03-31 | -152,883.00 Cr |
| 2025-03-31 | -139,967.00 Cr |
| 2026-03-31 | -122,916.00 Cr |
```

## `trademcp_screen_stocks`

*Fundamental + technical screen*

```json
{
  "universe": "NIFTY 50",
  "min_roe": 15,
  "max_debt_to_equity": 1.0,
  "limit": 5
}
```

Took 5.09s.

```markdown
# Stock screen - NIFTY 50

## Universe

NIFTY 50

## Symbols Scanned

50

## With Fundamentals

50

## Passed Fundamental Filters

16

## Final Matches

5

## Filters

| Metric             | Value |
|--------------------|-------|
| Min Pe             | -     |
| Max Pe             | -     |
| Min Roe            | 15.00 |
| Min Roce           | -     |
| Min Net Margin     | -     |
| Max Debt To Equity | 1.00  |
| Min Market Cap     | -     |
| Min Dividend Yield | -     |
| Min Current Ratio  | -     |
| Min Revenue Cagr   | -     |
| Rsi Below          | -     |
| Rsi Above          | -     |
| Above Sma50        | -     |
| Above Sma200       | -     |

## Elapsed Seconds

5.10

## Matches

| Symbol     | Price    | Market Cap    | Pe Ratio | Price To Book | Ev To Ebitda | Roe Pct | Roce Pct | Net Margin Pct | Debt To Equity | Current Ratio | Revenue Cagr 3Y Pct | Dividend Yield Pct | Health Score |
|------------|----------|---------------|----------|---------------|--------------|---------|----------|----------------|----------------|---------------|---------------------|--------------------|--------------|
| TCS        | 2,460.90 | 890,375.14 Cr | 17.25    | 7.48          | 9.92         | 45.89   | 62.21    | 18.43          | 0.11           | 2.23          | 5.80                | 1.95               | 94.30        |
| INFY       | 1,130.70 | 457,972.33 Cr | 15.40    | 5.01          | 7.98         | 33.85   | 46.53    | 16.44          | 0.10           | 1.98          | 3.44                | 4.42               | 89.30        |
| HINDUNILVR | 1,853.20 | 435,426.24 Cr | 41.55    | 8.93          | 28.47        | 30.86   | 29.18    | 23.59          | 0.03           | 1.22          | 2.31                | 2.37               | 88.30        |
| HCLTECH    | 1,379.90 | 373,368.74 Cr | 20.42    | 4.95          | 11.51        | 22.14   | 30.50    | 12.79          | 0.07           | 2.22          | 8.65                | 3.48               | 96.40        |
| ITC        | 260.80   | 326,795.87 Cr | 16.46    | 4.51          | 10.91        | 28.53   | 37.65    | 26.45          | 0.03           | 3.04          | 3.65                | 6.14               | 88.70        |
```

## `trademcp_analyze_portfolio`

*Portfolio risk and concentration*

```json
{
  "holdings": [
    {
      "symbol": "RELIANCE",
      "quantity": 10,
      "cost_price": 1150
    },
    {
      "symbol": "TCS",
      "quantity": 5,
      "cost_price": 2600
    }
  ]
}
```

Took 0.06s.

```markdown
# Portfolio analysis

## Holdings Count

2

## Total Market Value

24,324.50

## Total Cost

24,500.00

## Total Profit Loss

-175.50

## Total Profit Loss Pct

-0.72

## Holdings

| Symbol   | Name                              | Industry                   | Quantity | Cost Price | Current Price | Market Value | Profit Loss | Profit Loss Pct | Technical Score | Technical Label | Rsi 14 | Distance From 52W High Pct | Weight Pct |
|----------|-----------------------------------|----------------------------|----------|------------|---------------|--------------|-------------|-----------------|-----------------|-----------------|--------|----------------------------|------------|
| RELIANCE | Reliance Industries Limited       | Oil Gas & Consumable Fuels | 10.00    | 1,150.00   | 1,202.00      | 12,020.00    | 520.00      | 4.52            | -2.70           | Neutral         | 46.58  | -25.42                     | 49.42      |
| TCS      | Tata Consultancy Services Limited | Information Technology     | 5.00     | 2,600.00   | 2,460.90      | 12,304.50    | -695.50     | -5.35           | 31.70           | Buy             | 72.98  | -26.54                     | 50.58      |

## Allocation

### Sector Weights Pct

| Metric                     | Value |
|----------------------------|-------|
| Information Technology     | 50.58 |
| Oil Gas & Consumable Fuels | 49.42 |

### Largest Position

TCS

### Largest Position Weight Pct

50.58

### Best Performer

RELIANCE

### Best Performer Profit Pct

4.52

### Worst Performer

TCS

### Worst Performer Profit Pct

-5.35


## Risk

| Metric                    | Value    |
|---------------------------|----------|
| Beta                      | 0.88     |
| Annualised Alpha Pct      | -0.09    |
| Annualised Volatility Pct | 19.35    |
| Sharpe Ratio              | -0.97    |
| Sortino Ratio             | -0.95    |
| Max Drawdown Pct          | -32.11   |
| Benchmark                 | NIFTY 50 |
| Benchmark Return Pct      | -11.43   |
| Portfolio Return Pct      | -18.22   |
| Days Compared             | 246      |
| Excess Return Pct         | -6.79    |

## Flags

- Information Technology is 50.58% of the portfolio - concentration risk.
- Oil Gas & Consumable Fuels is 49.42% of the portfolio - concentration risk.
- RELIANCE is 49.42% of the portfolio - single-stock concentration.
- TCS is 50.58% of the portfolio - single-stock concentration.
- Fewer than 4 holdings - limited diversification.
```

