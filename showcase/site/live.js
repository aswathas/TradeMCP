/* ==========================================================================
   TradeMCP showcase — live layer.

   Talks to the showcase server's /api/* endpoints, which call the MCP server's
   own tools. So the live numbers on this page are the product's real output.
   Where those endpoints are absent (the folder opened as plain static files),
   the page falls back to data/snapshot.json, which is written by the same
   tools, and says so on screen.
   ========================================================================== */

const API = "api";
const SNAPSHOT_URL = "data/snapshot.json";

const TAPE_SYMBOLS = [
  "RELIANCE", "TCS", "INFY", "HDFCBANK",
  "SBIN", "ITC", "BPCL", "COALINDIA",
];

const SYMBOL_LIST = [
  ...TAPE_SYMBOLS,
  "TATAMOTORS", "TMCV", "AXISBANK", "KOTAKBANK", "LT", "MARUTI",
  "WIPRO", "HINDUNILVR", "BAJFINANCE", "ASIANPAINT", "SUNPHARMA",
  "TITAN", "ULTRACEMCO", "ADANIENT", "BHARTIARTL", "NTPC", "POWERGRID",
  "ONGC", "COALINDIA", "JSWSTEEL", "TATASTEEL", "HINDALCO", "SBILIFE",
  "BAJAJFINSV", "M&M", "HCLTECH", "TECHM", "TCS", "INDUSINDBK", "NESTLEIND",
];

const state = {
  symbol: "RELIANCE",
  candles: [],
  live: false,
  stamp: "",
  computed: null,
};

/* ---------- fetch helpers ------------------------------------------------ */

async function getJSON(path, timeoutMs = 20000) {
  const url = path.startsWith("http") ? path : `${API}/${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

async function loadSnapshot() {
  const res = await fetch(SNAPSHOT_URL);
  if (!res.ok) throw new Error(`snapshot HTTP ${res.status}`);
  return res.json();
}

function chartPath(symbol) {
  return `history?symbol=${encodeURIComponent(symbol)}&range=6mo`;
}

function fundamentalsPath(symbol) {
  return `fundamentals?symbol=${encodeURIComponent(symbol)}`;
}

/* ---------- indicator maths (mirrors the server's pure-python engine) ---- */

function sma(values, period) {
  const out = new Array(values.length).fill(null);
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

function ema(values, period) {
  const out = new Array(values.length).fill(null);
  const k = 2 / (period + 1);
  let prev = null;
  for (let i = 0; i < values.length; i += 1) {
    prev = prev === null ? values[i] : values[i] * k + prev * (1 - k);
    if (i >= period - 1) out[i] = prev;
  }
  return out;
}

function rsi(closes, period = 14) {
  const out = new Array(closes.length).fill(null);
  let avgGain = 0;
  let avgLoss = 0;
  for (let i = 1; i < closes.length; i += 1) {
    const change = closes[i] - closes[i - 1];
    const gain = Math.max(change, 0);
    const loss = Math.max(-change, 0);
    if (i <= period) {
      avgGain = (avgGain * (i - 1) + gain) / i;
      avgLoss = (avgLoss * (i - 1) + loss) / i;
      if (i === period) out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
    } else {
      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;
      out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
    }
  }
  return out;
}

function macd(closes, fast = 12, slow = 26, signalPeriod = 9) {
  const fastLine = ema(closes, fast);
  const slowLine = ema(closes, slow);
  const line = closes.map((_, i) =>
    fastLine[i] !== null && slowLine[i] !== null ? fastLine[i] - slowLine[i] : null);
  const dense = line.map((v) => (v === null ? null : v));
  const firstIdx = dense.findIndex((v) => v !== null);
  if (firstIdx === -1) {
    return { macd: line, signal: new Array(closes.length).fill(null), hist: new Array(closes.length).fill(null) };
  }
  const signal = new Array(closes.length).fill(null);
  const k = 2 / (signalPeriod + 1);
  let prev = null;
  for (let i = firstIdx; i < dense.length; i += 1) {
    prev = prev === null ? dense[i] : dense[i] * k + prev * (1 - k);
    signal[i] = prev;
  }
  const hist = dense.map((v, i) => (v !== null && signal[i] !== null ? v - signal[i] : null));
  return { macd: line, signal, hist };
}

function bollinger(closes, period = 20, mult = 2) {
  const mid = sma(closes, period);
  const upper = new Array(closes.length).fill(null);
  const lower = new Array(closes.length).fill(null);
  const percentB = new Array(closes.length).fill(null);
  for (let i = period - 1; i < closes.length; i += 1) {
    let variance = 0;
    for (let j = i - period + 1; j <= i; j += 1) variance += (closes[j] - mid[i]) ** 2;
    const sd = Math.sqrt(variance / period);
    upper[i] = mid[i] + mult * sd;
    lower[i] = mid[i] - mult * sd;
    percentB[i] = upper[i] === lower[i] ? 0.5 : (closes[i] - lower[i]) / (upper[i] - lower[i]);
  }
  return { mid, upper, lower, percentB };
}

function trueRanges(candles) {
  const out = [null];
  for (let i = 1; i < candles.length; i += 1) {
    const c = candles[i];
    const prevClose = candles[i - 1].close;
    out.push(Math.max(c.high - c.low, Math.abs(c.high - prevClose), Math.abs(c.low - prevClose)));
  }
  return out;
}

function atr(candles, period = 14) {
  const tr = trueRanges(candles);
  const out = new Array(candles.length).fill(null);
  let prev = null;
  for (let i = 0; i < tr.length; i += 1) {
    if (tr[i] === null) continue;
    if (i < period) {
      prev = prev === null ? tr[i] : prev + (tr[i] - prev) / (i + 1);
      if (i === period - 1) out[i] = prev;
    } else {
      prev = (prev * (period - 1) + tr[i]) / period;
      out[i] = prev;
    }
  }
  return out;
}

function stochastic(candles, period = 14) {
  const k = new Array(candles.length).fill(null);
  const d = new Array(candles.length).fill(null);
  for (let i = period - 1; i < candles.length; i += 1) {
    let hi = -Infinity;
    let lo = Infinity;
    for (let j = i - period + 1; j <= i; j += 1) {
      hi = Math.max(hi, candles[j].high);
      lo = Math.min(lo, candles[j].low);
    }
    k[i] = hi === lo ? 50 : ((candles[i].close - lo) / (hi - lo)) * 100;
  }
  for (let i = 0; i < k.length; i += 1) {
    if (k[i] === null) continue;
    const window = k.slice(Math.max(0, i - 2), i + 1).filter((v) => v !== null);
    d[i] = window.length ? window.reduce((a, b) => a + b, 0) / window.length : null;
  }
  return { k, d };
}

function obv(candles) {
  const out = [0];
  for (let i = 1; i < candles.length; i += 1) {
    const diff = candles[i].close - candles[i - 1].close;
    out.push(out[i - 1] + (diff > 0 ? candles[i].volume : diff < 0 ? -candles[i].volume : 0));
  }
  return out;
}

function vwap(candles) {
  const out = new Array(candles.length).fill(null);
  let pv = 0;
  let vol = 0;
  for (let i = 0; i < candles.length; i += 1) {
    const c = candles[i];
    const typical = (c.high + c.low + c.close) / 3;
    pv += typical * c.volume;
    vol += c.volume;
    out[i] = vol ? pv / vol : null;
  }
  return out;
}

/* ---------- formatting ---------------------------------------------------- */

const nf = (v, digits = 2) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "—"
    : v.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });

function fmtCompact(v) {
  if (v === null || v === undefined) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e7) return `${(v / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `${(v / 1e5).toFixed(2)} L`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(2)} K`;
  return nf(v);
}

/* Indian numbering reads in crore, so a rupee amount says "260,673 Cr" and
   not "2606730000000". */
function crore(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return (v / 1e7).toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function toCandles(payload) {
  const candles = payload?.candles || [];
  return {
    rows: candles.map((c) => ({
      date: c.date,
      open: c.open ?? c.close,
      high: c.high ?? c.close,
      low: c.low ?? c.close,
      close: c.close,
      volume: c.volume || 0,
    })),
    meta: payload || {},
  };
}

/* ---------- chart -------------------------------------------------------- */

const CH = { w: 900, h: 380, priceTop: 8, priceBottom: 226, volTop: 238, volBottom: 292, rsiTop: 304, rsiBottom: 372 };

function svgEl(name, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

function linePath(values, xOf, yOf) {
  let d = "";
  let open = false;
  values.forEach((v, i) => {
    if (v === null || v === undefined) { open = false; return; }
    d += `${open ? "L" : "M"}${xOf(i).toFixed(1)},${yOf(v).toFixed(1)}`;
    open = true;
  });
  return d;
}

function renderChart(candles) {
  const host = document.getElementById("chart");
  if (!host) return;
  host.textContent = "";
  if (!candles.length) {
    host.innerHTML = '<p class="chart__empty">No candles returned.</p>';
    return;
  }

  const closes = candles.map((c) => c.close);
  const volumes = candles.map((c) => c.volume);
  const bands = bollinger(closes, 20, 2);
  const mid20 = sma(closes, 20);
  const mid50 = sma(closes, 50);
  const rsiSeries = rsi(closes, 14);

  const visible = candles.map((c) => c.close);
  const allValues = visible.concat(bands.upper.filter((v) => v !== null), bands.lower.filter((v) => v !== null));
  let lo = Math.min(...allValues);
  let hi = Math.max(...allValues);
  const pad = (hi - lo) * 0.06 || 1;
  lo -= pad; hi += pad;

  const maxVol = Math.max(...volumes, 1);
  const xOf = (i) => (i / Math.max(candles.length - 1, 1)) * (CH.w - 8) + 4;
  const yOf = (v) => CH.priceBottom - ((v - lo) / (hi - lo)) * (CH.priceBottom - CH.priceTop);

  const svg = svgEl("svg", {
    viewBox: `0 0 ${CH.w} ${CH.h}`,
    preserveAspectRatio: "none",
    role: "img",
    "aria-label": `Price chart for ${state.symbol}, ${candles.length} daily candles.`,
    class: "chart__svg",
  });

  // the glowing area under the price line, coloured by the active domain
  const defs = svgEl("defs");
  const fill = svgEl("linearGradient", { id: "priceFill", x1: "0", y1: "0", x2: "0", y2: "1" });
  fill.appendChild(svgEl("stop", { offset: "0%", class: "chart__area-stop" }));
  fill.appendChild(svgEl("stop", { offset: "100%", class: "chart__area-stop chart__area-stop--low" }));
  defs.appendChild(fill);
  svg.appendChild(defs);

  let areaD = "";
  closes.forEach((v, i) => {
    areaD += `${areaD ? "L" : "M"}${xOf(i).toFixed(1)},${yOf(v).toFixed(1)}`;
  });
  areaD += `L${xOf(closes.length - 1).toFixed(1)},${CH.priceBottom}L${xOf(0).toFixed(1)},${CH.priceBottom}Z`;
  svg.appendChild(svgEl("path", { d: areaD, class: "chart__area" }));

  // grid + price axis labels
  for (let g = 0; g <= 4; g += 1) {
    const v = lo + ((hi - lo) * g) / 4;
    const y = yOf(v);
    svg.appendChild(svgEl("line", { x1: 0, y1: y, x2: CH.w, y2: y, class: "chart__grid" }));
    const label = svgEl("text", { x: 4, y: y - 4, class: "chart__axis" });
    label.textContent = nf(v, 0);
    svg.appendChild(label);
  }

  // bollinger band
  let bandD = "";
  bands.upper.forEach((v, i) => {
    if (v === null) return;
    bandD += `${bandD ? "L" : "M"}${xOf(i).toFixed(1)},${yOf(v).toFixed(1)}`;
  });
  for (let i = bands.lower.length - 1; i >= 0; i -= 1) {
    if (bands.lower[i] === null) continue;
    bandD += `L${xOf(i).toFixed(1)},${yOf(bands.lower[i]).toFixed(1)}`;
  }
  svg.appendChild(svgEl("path", { d: `${bandD}Z`, class: "chart__band" }));

  // volume bars
  candles.forEach((c, i) => {
    const h = (c.volume / maxVol) * (CH.volBottom - CH.volTop);
    const x = xOf(i);
    const w = Math.max((CH.w / candles.length) * 0.6, 1);
    svg.appendChild(svgEl("rect", {
      x: x - w / 2, y: CH.volBottom - h, width: w, height: h,
      class: c.close >= c.open ? "chart__vol-up" : "chart__vol-down",
    }));
  });

  // rsi panel
  [30, 70].forEach((level) => {
    const y = CH.rsiBottom - (level / 100) * (CH.rsiBottom - CH.rsiTop);
    svg.appendChild(svgEl("line", { x1: 0, y1: y, x2: CH.w, y2: y, class: "chart__rsi-line" }));
  });
  svg.appendChild(svgEl("path", { d: linePath(rsiSeries, xOf, (v) => CH.rsiBottom - (v / 100) * (CH.rsiBottom - CH.rsiTop)), class: "chart__rsi" }));

  // overlays
  svg.appendChild(svgEl("path", { d: linePath(mid50, xOf, yOf), class: "chart__sma50" }));
  svg.appendChild(svgEl("path", { d: linePath(mid20, xOf, yOf), class: "chart__sma20" }));
  svg.appendChild(svgEl("path", { d: linePath(closes, xOf, yOf), class: "chart__price" }));

  // last price marker
  const lastY = yOf(closes[closes.length - 1]);
  svg.appendChild(svgEl("line", { x1: 0, y1: lastY, x2: CH.w, y2: lastY, class: "chart__last-line" }));

  // Sukuna's attacks, drawn into the data: the cleave across the biggest
  // single move and the divine flame over the best day. Shrine only.
  let cleaveIdx = -1;
  let cleaveMag = 0;
  let flameIdx = -1;
  let flameMag = 0;
  candles.forEach((c, i) => {
    if (!c.open) return;
    const move = Math.abs(c.close - c.open) / c.open;
    if (move > cleaveMag) {
      cleaveMag = move;
      cleaveIdx = i;
    }
    const gain = (c.close - c.open) / c.open;
    if (gain > flameMag) {
      flameMag = gain;
      flameIdx = i;
    }
  });
  if (cleaveIdx >= 0) {
    const x = xOf(cleaveIdx);
    svg.appendChild(svgEl("line", {
      x1: x - 30, y1: CH.priceTop - 8, x2: x + 30, y2: CH.priceBottom + 8,
      class: "chart__cleave",
    }));
  }
  if (flameIdx >= 0) {
    const x = xOf(flameIdx);
    const y = yOf(candles[flameIdx].close);
    const flame = svgEl("g", {
      class: "chart__flame",
      transform: `translate(${x.toFixed(1)} ${y.toFixed(1)})`,
    });
    flame.appendChild(svgEl("path", { d: "M0 0 C 7 -7 5 -16 0 -25 C -5 -16 -7 -7 0 0 Z", class: "chart__flame-core" }));
    flame.appendChild(svgEl("path", { d: "M0 -3 C 3.5 -7 2.5 -13 0 -17 C -2.5 -13 -3.5 -7 0 -3 Z", class: "chart__flame-inner" }));
    svg.appendChild(flame);
  }

  host.appendChild(svg);

  // The finger tracker: one seal per session over the last 20 days, filled
  // when the day closed up. The six eyes read the same series by week.
  const seals = document.getElementById("tracker-seals");
  if (seals) {
    const recent = candles.slice(-20);
    seals.textContent = "";
    let up = 0;
    recent.forEach((c) => {
      const gain = c.open ? c.close >= c.open : true;
      if (gain) up += 1;
      const cell = document.createElement("span");
      cell.className = gain ? "seal seal--up" : "seal";
      seals.appendChild(cell);
    });
    const count = document.getElementById("tracker-count");
    if (count) count.textContent = `${up} / ${recent.length} seals converged`;
  }

  const lenses = document.getElementById("tracker-lenses");
  if (lenses) {
    lenses.textContent = "";
    let charged = 0;
    for (let w = 0; w < 6; w += 1) {
      const from = Math.max(0, candles.length - (w + 1) * 5);
      const to = candles.length - w * 5;
      const slice = candles.slice(from, to);
      const gain = slice.length > 1 && slice[0].close > 0
        ? (slice[slice.length - 1].close - slice[0].close) / slice[0].close
        : 0;
      if (gain > 0) charged += 1;
      const cell = document.createElement("span");
      cell.className = gain > 0 ? "lens lens--charged" : "lens";
      lenses.appendChild(cell);
    }
    const lc = document.getElementById("lenses-count");
    if (lc) lc.textContent = `${charged} / 6 lenses charged`;
  }

  const legend = document.getElementById("chart-legend");
  if (legend) {
    legend.innerHTML = `
      <span class="legend"><i class="legend__key legend__key--price"></i>Close</span>
      <span class="legend"><i class="legend__key legend__key--sma20"></i>SMA 20</span>
      <span class="legend"><i class="legend__key legend__key--sma50"></i>SMA 50</span>
      <span class="legend"><i class="legend__key legend__key--band"></i>Bollinger 20·2</span>
      <span class="legend"><i class="legend__key legend__key--rsi"></i>RSI 14</span>
      <span class="legend legend--shrine"><i class="legend__key legend__key--cleave"></i>Cleave</span>
      <span class="legend legend--shrine"><i class="legend__key legend__key--flame"></i>Divine flame</span>
      <span class="legend legend--right">${candles[0].date} → ${candles[candles.length - 1].date}</span>`;
  }

  return { closes, bands, mid20, mid50, rsiSeries };
}

/* ---------- readouts ----------------------------------------------------- */

function setReadouts(rows, hostId, tone) {
  const host = document.getElementById(hostId);
  if (!host) return;
  host.textContent = "";
  for (const row of rows) {
    const item = document.createElement("div");
    item.className = "readout";
    const label = document.createElement("span");
    label.className = "readout__label";
    label.textContent = row.label;
    const value = document.createElement("span");
    value.className = `readout__value${row.tone ? ` readout__value--${row.tone}` : ""}`;
    value.textContent = row.value;
    const hint = document.createElement("span");
    hint.className = "readout__hint";
    hint.textContent = row.hint || "";
    item.append(label, value, hint);
    host.appendChild(item);
  }
  if (tone) host.dataset.tone = tone;
}

function buildIndicatorRows(candles, computed) {
  if (!computed) return [];
  const { closes, bands, mid20, mid50, rsiSeries } = computed;
  const last = closes.length - 1;
  const macdSeries = macd(closes);
  const atrSeries = atr(candles, 14);
  const stoch = stochastic(candles, 14);
  const obvSeries = obv(candles);
  const vwapSeries = vwap(candles);
  const volSma = sma(candles.map((c) => c.volume), 20);
  const lastVol = candles[last].volume;
  const avgVol = volSma[last];

  const signal = (v, bandsHint = "") => {
    if (v === null || v === undefined) return "—";
    if (v > 70) return "overbought";
    if (v < 30) return "oversold";
    return bandsHint;
  };

  return [
    { label: "RSI 14", value: nf(rsiSeries[last], 2), hint: signal(rsiSeries[last], "neutral"), tone: rsiSeries[last] > 70 ? "down" : rsiSeries[last] < 30 ? "up" : "" },
    { label: "MACD (12·26·9)", value: nf(macdSeries.macd[last], 2), hint: `signal ${nf(macdSeries.signal[last], 2)}` },
    { label: "Stochastic %K", value: nf(stoch.k[last], 2), hint: `%D ${nf(stoch.d[last], 2)}` },
    { label: "ATR 14", value: nf(atrSeries[last], 2), hint: "avg true range" },
    { label: "SMA 20", value: nf(mid20[last], 2), hint: close > mid20[last] ? "price above" : "price below", tone: mid20[last] === null ? "" : closes[last] > mid20[last] ? "up" : "down" },
    { label: "SMA 50", value: nf(mid50[last], 2), hint: close > mid50[last] ? "price above" : "price below", tone: mid50[last] === null ? "" : closes[last] > mid50[last] ? "up" : "down" },
    { label: "Bollinger %B", value: nf(bands.percentB[last], 2), hint: "0 = lower, 1 = upper" },
    { label: "VWAP", value: nf(vwapSeries[last], 2), hint: "volume weighted" },
    { label: "OBV", value: fmtCompact(obvSeries[last]), hint: "on balance volume" },
    { label: "Volume vs 20d", value: avgVol ? `${nf(lastVol / avgVol, 2)}×` : "—", hint: "today vs 20d average" },
  ];
}

function buildFundamentalRows(f) {
  if (!f) return [];
  const pct = (v) => (v === null || v === undefined ? "—" : `${nf(v, 2)}%`);
  const x = (v) => (v === null || v === undefined ? "—" : nf(v, 2));
  return [
    { label: "Market cap", value: fmtCompact(f.marketCap), hint: "trailing" },
    { label: "P/E", value: x(f.pe), hint: "trailing" },
    { label: "P/B", value: x(f.priceToBook), hint: "equity ÷ shares" },
    { label: "EV/EBITDA", value: x(f.evToEbitda), hint: "enterprise value" },
    { label: "ROE", value: pct(f.roe), hint: "return on equity" },
    { label: "ROA", value: pct(f.roa), hint: "return on assets" },
    { label: "Net margin", value: pct(f.netMargin), hint: "net income ÷ revenue" },
    { label: "Debt / equity", value: x(f.debtToEquity), hint: "total debt ÷ equity" },
    { label: "Current ratio", value: x(f.currentRatio), hint: "current assets ÷ liabilities" },
    { label: "Quick ratio", value: x(f.quickRatio), hint: "inventory excluded" },
    { label: "Dividend yield", value: pct(f.dividendYield), hint: "trailing" },
    { label: "Net debt", value: fmtCompact(f.netDebt), hint: "debt − cash" },
  ];
}

/* ---------- ticker tape --------------------------------------------------- */

function tapeItem(entry) {
  const up = (entry.change_pct || 0) >= 0;
  const item = document.createElement("span");
  item.className = `tape__item${up ? "" : " tape__item--down"}`;
  const arrow = up ? "▲" : "▼";
  item.innerHTML =
    `<b>${entry.symbol}</b>` +
    `<span class="tape__price">${nf(entry.price, 2)}</span>` +
    `<span class="tape__change">${arrow} ${nf(Math.abs(entry.change_pct || 0), 2)}%</span>`;
  return item;
}

function paintTape(rows, rowId, reverse) {
  const row = document.getElementById(rowId);
  if (!row || !rows.length) return;
  row.textContent = "";
  const doubled = [...rows, ...rows];
  for (const entry of doubled) row.appendChild(tapeItem(entry));
  row.classList.toggle("tape__row--reverse", Boolean(reverse));
}

async function refreshTape(snapshotTape) {
  let rows = null;
  try {
    const payload = await getJSON("tape", 20000);
    if (Array.isArray(payload) && payload.length) rows = payload;
  } catch {
    rows = null;
  }
  if (!rows) rows = snapshotTape || [];
  if (!rows.length) return;
  paintTape(rows, "tape-row-a", false);
  paintTape([...rows].reverse(), "tape-row-b", true);
  setTapeStamp(rows === snapshotTape ? "snapshot" : new Date().toLocaleTimeString("en-IN"));
}

function setTapeStamp(text) {
  const node = document.getElementById("tape-stamp");
  if (node) node.textContent = text;
}

/* ---------- board -------------------------------------------------------- */

function setBadge(live, stamp) {
  const badge = document.getElementById("board-badge");
  const stampNode = document.getElementById("board-stamp");
  if (badge) {
    badge.textContent = live ? "LIVE" : "SNAPSHOT";
    badge.classList.toggle("board__badge--live", live);
  }
  if (stampNode) stampNode.textContent = stamp || "";
}

/* The server's quote and the bundled snapshot spell the 52-week band
   differently; normalise both onto one shape. */
function normaliseQuote(raw) {
  if (!raw) return null;
  return {
    name: raw.name || null,
    price: raw.price ?? null,
    change_pct: raw.change_pct ?? null,
    high: raw.week_52_high ?? raw["52_week_high"] ?? null,
    low: raw.week_52_low ?? raw["52_week_low"] ?? null,
  };
}

/* A live number that rolls when it changes: only the digits that moved flip. */
function rollNumber(node, text) {
  if (!node) return;
  const prev = node.textContent || "";
  if (prev === text) return;
  node.textContent = "";
  const frag = document.createDocumentFragment();
  for (let i = 0; i < text.length; i += 1) {
    const span = document.createElement("span");
    span.className = "digit";
    span.textContent = text[i];
    if (prev[i] && prev[i] !== text[i]) span.classList.add("digit--changed");
    frag.appendChild(span);
  }
  node.appendChild(frag);
}

function setPrice(rawQuote) {
  const quote = normaliseQuote(rawQuote);
  if (!quote || quote.price === null) return;
  const last = document.getElementById("board-last");
  const change = document.getElementById("board-change");
  const range = document.getElementById("board-range");
  const nameNode = document.getElementById("board-name");

  if (last) rollNumber(last, nf(quote.price, 2));
  if (change && quote.change_pct !== null) {
    const up = quote.change_pct >= 0;
    rollNumber(change, `${up ? "▲" : "▼"} ${nf(Math.abs(quote.change_pct), 2)}%`);
    change.className = `board__change ${up ? "is-up" : "is-down"}`;
    // The powers are components, not themes: the live tick reads as a pull
    // (Ao) when the price rises and a push (Aka) when it falls.
    const power = up ? "ao" : "aka";
    const tendency = document.getElementById("tech-tendency");
    const tickText = document.getElementById("tick-text");
    if (tendency) tendency.dataset.tone = power;
    if (tickText) tickText.textContent = up ? "Live tick ▸ AO attract" : "Live tick ▸ AKA repel";
  }
  if (range && quote.high && quote.low) {
    const pos = ((quote.price - quote.low) / (quote.high - quote.low)) * 100;
    range.innerHTML =
      `<span class="board__range-label">52-week range</span>` +
      `<span class="board__range-track"><i style="left:${pos.toFixed(1)}%"></i></span>` +
      `<span class="board__range-nums">${nf(quote.low, 2)} — ${nf(quote.high, 2)}</span>`;
  }
  if (nameNode && quote.name) nameNode.textContent = quote.name;
  const feed = document.getElementById("board-feed-label");
  if (feed) feed.textContent = "live feed";
}
/* ---------- the hero HUD ----------------------------------------------------
   The first screen used to be static markup with a LIVE tag over snapshot
   numbers. It is now painted from the same payloads the live board uses, so
   every figure on it is the server's real output.
   ------------------------------------------------------------------------- */

function hudSet(id, text) {
  const node = document.getElementById(id);
  if (node && text !== null && text !== undefined && text !== "") node.textContent = text;
}

/* The live quote and the bundled snapshot spell the 52-week band differently. */
function hudQuote(raw) {
  if (!raw) return null;
  const price = raw.price ?? null;
  const high = raw.week_52_high ?? raw["52_week_high"] ?? null;
  const low = raw.week_52_low ?? raw["52_week_low"] ?? null;
  let position = null;
  if (price !== null && high && low && high > low) {
    position = ((price - low) / (high - low)) * 100;
  }
  return {
    price,
    change: raw.change_pct ?? null,
    high,
    low,
    volume: raw.volume ?? null,
    position,
  };
}

function paintHud(quote, fundamentals, score, rsi, live) {
  if (!quote && !fundamentals) return;

  const tag = document.getElementById("hud-tag");
  const tagText = document.getElementById("hud-tag-text");
  if (tag) tag.classList.toggle("hud-tag--snapshot", !live);
  if (tagText) tagText.textContent = live ? "LIVE · RELIANCE INDUSTRIES · NSE" : "SNAPSHOT · RELIANCE INDUSTRIES · NSE";
  hudSet("hud-title", live ? "Live analysis panel" : "Analysis panel");

  if (quote) {
    if (quote.price !== null) rollNumber(document.getElementById("hud-price"), nf(quote.price, 2));
    if (quote.change !== null && quote.change !== undefined) {
      const up = quote.change >= 0;
      const holder = document.getElementById("hud-change");
      hudSet("hud-change-value", `${up ? "+" : "−"}${nf(Math.abs(quote.change), 2)}`);
      hudSet("hud-arrow", up ? "▲" : "▼");
      if (holder) {
        holder.classList.toggle("hud-value--down", !up);
        holder.classList.toggle("hud-value--up", up);
      }
    }
    if (quote.volume !== null && quote.volume !== undefined) {
      hudSet("hud-volume", `on ${crore(quote.volume, 2)} Cr volume`);
    }
    if (quote.high && quote.low) {
      hudSet("hud-range-low", nf(quote.low, 2));
      hudSet("hud-range-high", nf(quote.high, 2));
      if (quote.price !== null) hudSet("hud-range-price", nf(quote.price, 2));
      if (quote.position !== null) {
        const marker = document.getElementById("hud-range-marker");
        if (marker) marker.style.left = `${quote.position.toFixed(1)}%`;
        const band = document.getElementById("hud-range");
        if (band && quote.price !== null) {
          band.setAttribute(
            "aria-label",
            `Price ${nf(quote.price, 2)} sits ${quote.position.toFixed(1)} percent up a 52-week range from ${nf(quote.low, 2)} to ${nf(quote.high, 2)}.`
          );
        }
      }
    }
  }

  if (fundamentals) {
    const v = fundamentals.valuation || {};
    const p = fundamentals.profitability || {};
    const l = fundamentals.leverage || {};
    const q = fundamentals.liquidity || {};
    const h = fundamentals.health_score || {};

    if (v.pe_ratio !== undefined) hudSet("hud-pe", nf(v.pe_ratio, 2));
    if (p.return_on_equity_pct !== undefined) hudSet("hud-roe", nf(p.return_on_equity_pct, 2));
    if (p.roce_pct !== undefined) hudSet("hud-roce", nf(p.roce_pct, 2));
    if (l.debt_to_equity !== undefined) hudSet("hud-de", nf(l.debt_to_equity, 2));
    if (l.net_debt !== undefined && l.net_debt !== null) {
      hudSet("hud-netdebt", `net debt ₹${crore(l.net_debt, 0)} Cr`);
    }
    if (v.dividend_yield_pct !== undefined) hudSet("hud-dy", nf(v.dividend_yield_pct, 2));
    if (q.current_ratio !== undefined && q.current_ratio !== null) {
      hudSet("hud-cr", `current ratio ${nf(q.current_ratio, 2)}`);
    }
    if (h.score !== undefined && h.score !== null) {
      hudSet("hud-health-label", `Health score · ${nf(h.score, 2)}`);
      const fill = document.getElementById("hud-health-fill");
      if (fill) fill.style.width = `${Math.max(0, Math.min(100, h.score))}%`;
      const band = document.getElementById("hud-health");
      if (band) band.setAttribute("aria-label", `Health score ${nf(h.score, 2)} out of 100.`);
    }
  }

  if (rsi !== null && rsi !== undefined && !Number.isNaN(rsi)) {
    hudSet("hud-rsi-label", `RSI 14 · ${nf(rsi, 2)}`);
    const marker = document.getElementById("hud-rsi-marker");
    if (marker) marker.style.left = `${Math.max(0, Math.min(100, rsi))}%`;
    const band = document.getElementById("hud-rsi");
    if (band) {
      band.setAttribute(
        "aria-label",
        `RSI ${nf(rsi, 2)}, between the oversold 30 and overbought 70 bands.`
      );
    }
  }

  if (score && score.score !== null && score.score !== undefined) {
    const value = Number(score.score);
    const label = score.label || "—";
    hudSet("hud-score", `${value > 0 ? "+" : value < 0 ? "−" : ""}${nf(Math.abs(value), 2)}`);
    hudSet("hud-score-label", label);
    const needle = document.getElementById("hud-needle");
    if (needle) needle.style.left = `${Math.max(0, Math.min(100, (value + 100) / 2)).toFixed(1)}%`;
    const gauge = document.getElementById("hud-gauge");
    if (gauge) {
      gauge.setAttribute(
        "aria-label",
        `Technical score ${value.toFixed(2)} on a scale from minus 100 Strong Sell to plus 100 Strong Buy, reading ${label}.`
      );
    }
  }
}

async function refreshHud(snapshot) {
  const symbol = "RELIANCE";
  let quote = null;
  let fundamentals = null;
  let live = false;

  try {
    const [q, f] = await Promise.all([
      getJSON(`quote?symbol=${encodeURIComponent(symbol)}`, 20000),
      getJSON(fundamentalsPath(symbol), 20000),
    ]);
    quote = q;
    fundamentals = f;
    live = true;
  } catch {
    live = false;
  }

  if (!live) {
    const snap = snapshot?.fundamentals?.[symbol];
    if (snap) {
      fundamentals = snap;
      quote = snap.market || null;
    }
  }

  let score = null;
  if (live) {
    try {
      score = await getJSON(`score?symbol=${encodeURIComponent(symbol)}`, 25000);
    } catch {
      score = null;
    }
  }

  const series = state.computed?.rsiSeries;
  const rsi = series && series.length ? series[series.length - 1] : null;

  paintHud(hudQuote(quote), fundamentals, score, rsi, live);

  const foot = document.getElementById("hud-foot");
  if (foot) {
    const stamp = new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
    foot.textContent = live
      ? `Live from the TradeMCP server at ${stamp} — Yahoo Finance, NSE archives and Screener.in.`
      : "Server snapshot from Yahoo Finance, NSE archives and Screener.in — this host has no live endpoint.";
  }
}

async function refreshBoard(symbol, snapshot) {
  const badge = document.getElementById("board-badge");
  if (badge) badge.textContent = "…";
  try {
    const history = await getJSON(chartPath(symbol), 20000);
    const { rows } = toCandles(history);
    if (!rows.length) throw new Error("no candles");

    state.candles = rows;
    state.live = true;
    state.stamp = new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
    setBadge(true, state.stamp);

    const quote = await getJSON(`quote?symbol=${encodeURIComponent(symbol)}`, 20000);
    setPrice(quote);

    const computed = renderChart(rows);
    state.computed = computed;
    setReadouts(buildIndicatorRows(rows, computed), "indicator-list");

    try {
      const fundamentals = await getJSON(fundamentalsPath(symbol), 20000);
      setReadouts(buildFundamentalRows(fundamentalsFromFundamentals(fundamentals)), "fundamental-list");
    } catch {
      const fallback = snapshot?.fundamentals?.[symbol];
      if (fallback) setReadouts(buildFundamentalRows(fundamentalsFromFundamentals(fallback)), "fundamental-list");
    }
  } catch {
    state.live = false;
    paintSnapshot(symbol, snapshot, "server snapshot — live endpoint unavailable");
  }
}

/* The static fallback, used when the host has no /api/* endpoints. It paints
   everything the live path paints, so the deployed page is the same page. */
function paintSnapshot(symbol, snapshot, stamp) {
  const fallback = snapshot?.fundamentals?.[symbol];
  const candles = snapshot?.candles || [];
  if (candles.length) {
    const computed = renderChart(candles);
    state.computed = computed;
    setReadouts(buildIndicatorRows(candles, computed), "indicator-list");
  }
  if (fallback) {
    setReadouts(buildFundamentalRows(fundamentalsFromFundamentals(fallback)), "fundamental-list");
    setPrice(fallback.market || fallback);
  }
  const feed = document.getElementById("board-feed-label");
  if (feed) feed.textContent = "snapshot feed";
  setBadge(false, stamp || "server snapshot");
}
function fundamentalsFromFundamentals(payload) {
  const v = payload.valuation || {};
  const p = payload.profitability || {};
  const l = payload.leverage || {};
  const q = payload.liquidity || {};
  return {
    marketCap: v.market_cap ?? null,
    pe: v.pe_ratio ?? null,
    priceToBook: v.price_to_book ?? null,
    evToEbitda: v.ev_to_ebitda ?? null,
    roe: p.return_on_equity_pct ?? null,
    roa: p.return_on_assets_pct ?? null,
    netMargin: p.net_margin_pct ?? null,
    debtToEquity: l.debt_to_equity ?? null,
    currentRatio: q.current_ratio ?? null,
    quickRatio: q.quick_ratio ?? null,
    dividendYield: v.dividend_yield_pct ?? null,
    netDebt: l.net_debt ?? null,
  };
}

/* ---------- wiring -------------------------------------------------------- */

function wireBoard() {
  const input = document.getElementById("symbol-input");
  const list = document.getElementById("symbol-list");
  if (list) {
    list.innerHTML = SYMBOL_LIST.map((s) => `<option value="${s}"></option>`).join("");
  }
  if (!input) return;

  let snapshot = null;
  let timer = null;

  const run = async () => {
    const symbol = (input.value || "RELIANCE").trim().toUpperCase();
    state.symbol = symbol;
    await refreshBoard(symbol, snapshot);
    refreshHud(snapshot);
  };

  input.addEventListener("change", run);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); run(); }
  });

  const refresh = document.getElementById("board-refresh");
  if (refresh) refresh.addEventListener("click", run);

  loadSnapshot()
    .then((data) => {
      snapshot = data;
      // A static host has no /api/* endpoints: paint the board from the
      // snapshot the server itself wrote, and say so on screen.
      if (!state.live) {
        paintSnapshot(state.symbol || "RELIANCE", data, "server snapshot");
      }
      return refreshTape(data.tape || []);
    })
    .catch(() => refreshTape([]))
    .finally(() => refreshHud(snapshot));

  // The board runs immediately; the tape is a background extra and must never
  // hold up the headline numbers.
  run();

  timer = setInterval(run, 90000);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { clearInterval(timer); } else { run(); timer = setInterval(run, 90000); }
  });
}

wireBoard();
