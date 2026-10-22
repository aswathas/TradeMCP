/* ==========================================================================
   TradeMCP showcase — screener.

   Fifty real NIFTY 50 constituents with the metrics the server itself returns,
   pulled by scripts/refresh_screener_data.py through trademcp_screen_stocks
   and trademcp_compare_stocks. The filters here re-apply the same predicates
   the server applies server-side, and the panel prints the exact tool call
   that would produce the same result set.
   ========================================================================== */

(function () {

const PRESETS = {
  all: { label: "All 50", filters: {} },
  quality: {
    label: "Quality",
    filters: { minRoe: 15, minRoce: 15, maxDe: 1.5, minHealth: 60 },
    note: "return on equity, return on capital and a leverage ceiling",
  },
  value: {
    label: "Value",
    filters: { maxPe: 20, minHealth: 40 },
    note: "a price-to-earnings ceiling with a health floor",
  },
  dividend: {
    label: "Dividend",
    filters: { minDivYield: 3 },
    note: "trailing dividend yield",
  },
  growth: {
    label: "Growth",
    filters: { minRevCagr: 10, minRoe: 10 },
    note: "three-year revenue CAGR with a return on equity floor",
  },
  momentum: {
    label: "Momentum",
    filters: { minRsi: 50, maxRsi: 80 },
    note: "RSI band — the only filter the server applies on technicals",
  },
};

const DEFAULT_FILTERS = {
  search: "",
  maxPe: 800,
  minRoe: -50,
  minRoce: -50,
  minDivYield: 0,
  maxDe: 20,
  maxRsi: 100,
  minRsi: 0,
  minRevCagr: -100,
  minHealth: -500,
  minMarketCapCr: 0,
};

let screenerRows = [];
let screenerFilters = { ...DEFAULT_FILTERS };
let screenerSort = { key: "market_cap", dir: "desc" };

const nf = (v, digits = 2) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "—"
    : v.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });

function fmtCr(v) {
  if (v === null || v === undefined) return "—";
  return `${(v / 1e7).toFixed(0)}`;
}

function num(v) {
  return v === null || v === undefined || Number.isNaN(v) ? null : Number(v);
}

function applyFilters() {
  const f = screenerFilters;
  const q = f.search.trim().toLowerCase();
  return screenerRows.filter((row) => {
    if (q) {
      const hay = `${row.symbol} ${row.name || ""} ${row.industry || ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    const pe = num(row.pe_ratio);
    const roe = num(row.roe_pct);
    const roce = num(row.roce_pct);
    const div = num(row.dividend_yield_pct);
    const de = num(row.debt_to_equity);
    const rsi = num(row.rsi_14);
    const cagr = num(row.revenue_cagr_3y_pct);
    const health = num(row.health_score);
    const mcap = num(row.market_cap);

    if (pe !== null && pe > f.maxPe) return false;
    if (roe !== null && roe < f.minRoe) return false;
    if (roce !== null && roce < f.minRoce) return false;
    if (div !== null && div < f.minDivYield) return false;
    if (de !== null && de > f.maxDe) return false;
    if (rsi !== null && rsi > f.maxRsi) return false;
    if (rsi !== null && rsi < f.minRsi) return false;
    if (cagr !== null && cagr < f.minRevCagr) return false;
    if (health !== null && health < f.minHealth) return false;
    if (mcap !== null && mcap / 1e7 < f.minMarketCapCr) return false;
    return true;
  });
}

function sortRows(rows) {
  const { key, dir } = screenerSort;
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    if (av === null || av === undefined) return 1;
    if (bv === null || bv === undefined) return -1;
    if (typeof av === "string") return av.localeCompare(bv) * sign;
    return (av - bv) * sign;
  });
}

const COLUMNS = [
  { key: "symbol", label: "Symbol", type: "text" },
  { key: "price", label: "Price", type: "num" },
  { key: "change_pct", label: "Chg %", type: "num", tone: "change" },
  { key: "pe_ratio", label: "P/E", type: "num" },
  { key: "roe_pct", label: "ROE", type: "num" },
  { key: "roce_pct", label: "ROCE", type: "num" },
  { key: "net_margin_pct", label: "Net margin", type: "num" },
  { key: "debt_to_equity", label: "D/E", type: "num" },
  { key: "dividend_yield_pct", label: "Div yield", type: "num" },
  { key: "revenue_cagr_3y_pct", label: "Rev CAGR", type: "num" },
  { key: "health_score", label: "Health", type: "num" },
  { key: "rsi_14", label: "RSI", type: "num" },
  { key: "technical_label", label: "Signal", type: "text" },
];

function renderTable(rows) {
  const body = document.getElementById("sc-body");
  if (!body) return;
  body.textContent = "";

  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.dataset.symbol = row.symbol;

    const cells = [];
    /* The symbol is a button, not just a label: clicking a row loads it, and
       a keyboard has to be able to do the same thing. */
    cells.push(
      `<td class="sc-sym"><b><button type="button" class="sc-load" data-symbol="${row.symbol}">${row.symbol}</button></b><span>${row.name || ""}</span></td>`
    );
    cells.push(`<td class="num">${nf(row.price, 2)}</td>`);
    const chg = num(row.change_pct);
    cells.push(`<td class="num ${chg === null ? "" : chg >= 0 ? "is-up" : "is-down"}">${chg === null ? "—" : `${chg >= 0 ? "▲" : "▼"} ${nf(Math.abs(chg), 2)}`}</td>`);
    cells.push(`<td class="num">${nf(row.pe_ratio, 2)}</td>`);
    cells.push(`<td class="num">${nf(row.roe_pct, 2)}</td>`);
    cells.push(`<td class="num">${nf(row.roce_pct, 2)}</td>`);
    cells.push(`<td class="num">${nf(row.net_margin_pct, 2)}</td>`);
    cells.push(`<td class="num">${nf(row.debt_to_equity, 2)}</td>`);
    cells.push(`<td class="num">${nf(row.dividend_yield_pct, 2)}</td>`);
    cells.push(`<td class="num">${nf(row.revenue_cagr_3y_pct, 2)}</td>`);
    cells.push(`<td class="num">${nf(row.health_score, 1)}</td>`);
    cells.push(`<td class="num">${nf(row.rsi_14, 2)}</td>`);
    const label = row.technical_label || "";
    const tone = label.includes("Buy") ? "is-up" : label.includes("Sell") ? "is-down" : "";
    cells.push(`<td class="sc-signal ${tone}">${label || "—"}</td>`);

    tr.innerHTML = cells.join("");
    body.appendChild(tr);
  }
}

function renderHeader() {
  const head = document.getElementById("sc-head-row");
  if (!head) return;
  head.textContent = "";
  for (const col of COLUMNS) {
    const th = document.createElement("th");
    th.scope = "col";
    const active = screenerSort.key === col.key;
    th.className = `${col.type === "num" ? "num " : ""}${active ? "is-sorted" : ""}`;
    /* A sort control that only answers a mouse is not a control. The button
       gives it a name, a focus ring and Enter/Space for free. */
    const button = document.createElement("button");
    button.type = "button";
    button.className = "sc-sort";
    button.textContent = col.label;
    if (active) {
      const arrow = document.createElement("i");
      arrow.setAttribute("aria-hidden", "true");
      arrow.textContent = screenerSort.dir === "desc" ? "▼" : "▲";
      button.appendChild(arrow);
    }
    button.addEventListener("click", () => {
      if (screenerSort.key === col.key) {
        screenerSort.dir = screenerSort.dir === "desc" ? "asc" : "desc";
      } else {
        screenerSort.key = col.key;
        screenerSort.dir = col.type === "num" ? "desc" : "asc";
      }
      render();
    });
    th.appendChild(button);
    /* aria-sort belongs on the header cell, and it says which column is
       sorted and in which direction - or that none is. */
    if (active) {
      th.setAttribute("aria-sort", screenerSort.dir === "desc" ? "descending" : "ascending");
    } else {
      th.setAttribute("aria-sort", "none");
    }
    head.appendChild(th);
  }
}

function buildToolCall() {
  const f = screenerFilters;
  /* The table shows every row that passes; the call has to ask for the same
     number, or the panel prints a command that returns less than it shows. */
  const args = { universe: "NIFTY 50", limit: screenerRows.length || 50 };
  if (f.maxPe !== DEFAULT_FILTERS.maxPe) args.max_pe = f.maxPe;
  if (f.minRoe !== DEFAULT_FILTERS.minRoe) args.min_roe = f.minRoe;
  if (f.minRoce !== DEFAULT_FILTERS.minRoce) args.min_roce = f.minRoce;
  if (f.minDivYield !== DEFAULT_FILTERS.minDivYield) args.min_dividend_yield = f.minDivYield;
  if (f.maxDe !== DEFAULT_FILTERS.maxDe) args.max_debt_to_equity = f.maxDe;
  if (f.maxRsi !== DEFAULT_FILTERS.maxRsi) args.rsi_above = f.maxRsi;
  if (f.minRsi !== undefined && f.minRsi > 0) args.rsi_below = f.minRsi;
  if (f.minRevCagr !== DEFAULT_FILTERS.minRevCagr) args.min_revenue_cagr = f.minRevCagr;
  if (f.minMarketCapCr !== DEFAULT_FILTERS.minMarketCapCr) args.min_market_cap = f.minMarketCapCr * 1e7;
  args.sort_by = screenerSort.key === "market_cap" ? "market_cap" : screenerSort.key;
  args.sort_order = screenerSort.dir;

  const payload = { tool: "trademcp_screen_stocks", arguments: args };
  return JSON.stringify(payload, null, 2);
}

function render() {
  const filtered = applyFilters();
  const sorted = sortRows(filtered);
  renderTable(sorted);
  renderHeader();

  const count = document.getElementById("sc-count");
  if (count) count.textContent = `${sorted.length} / ${screenerRows.length}`;

  const call = document.getElementById("sc-json");
  if (call) call.textContent = buildToolCall();

  const note = document.getElementById("sc-note");
  if (note) {
    note.textContent = `Universe NIFTY 50 · metrics from ${screenerRows.length} constituents pulled by the server · ${sorted.length} pass the filters above`;
  }
}

function syncControls() {
  const f = screenerFilters;
  const set = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.value = value;
    const out = document.getElementById(`${id}-out`);
    if (out) out.textContent = value;
  };
  set("sc-maxpe", f.maxPe);
  set("sc-minroe", f.minRoe);
  set("sc-minroce", f.minRoce);
  set("sc-mindiv", f.minDivYield);
  set("sc-maxde", f.maxDe);
  set("sc-maxrsi", f.maxRsi);
  set("sc-minrsi", f.minRsi);
  set("sc-mincagr", f.minRevCagr);
  set("sc-minhealth", f.minHealth);
  set("sc-minmcap", f.minMarketCapCr);
}

const FILTER_INPUTS = [
  ["sc-maxpe", "maxPe"], ["sc-minroe", "minRoe"], ["sc-minroce", "minRoce"],
  ["sc-mindiv", "minDivYield"], ["sc-maxde", "maxDe"], ["sc-maxrsi", "maxRsi"],
  ["sc-minrsi", "minRsi"], ["sc-mincagr", "minRevCagr"], ["sc-minhealth", "minHealth"],
  ["sc-minmcap", "minMarketCapCr"],
];

function wire() {
  const search = document.getElementById("sc-search");
  if (search) {
    search.addEventListener("input", () => {
      screenerFilters.search = search.value;
      render();
    });
  }

  for (const [id, key] of FILTER_INPUTS) {
    const node = document.getElementById(id);
    if (!node) continue;
    node.addEventListener("input", () => {
      screenerFilters[key] = Number(node.value);
      const out = document.getElementById(`${id}-out`);
      if (out) out.textContent = node.value;
      render();
    });
  }

  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => {
      const preset = PRESETS[button.dataset.preset];
      screenerFilters = { ...DEFAULT_FILTERS, ...preset.filters, search: search ? search.value : "" };
      document.querySelectorAll("[data-preset]").forEach((other) => {
        other.classList.toggle("is-active", other === button);
        other.setAttribute("aria-pressed", String(other === button));
      });
      syncControls();
      render();
    });
  });

  const reset = document.getElementById("sc-reset");
  if (reset) {
    reset.addEventListener("click", () => {
      screenerFilters = { ...DEFAULT_FILTERS };
      if (search) search.value = "";
      syncControls();
      render();
    });
  }

  // Clicking a row loads that symbol into the live board.
  const loadSymbol = (symbol) => {
    const input = document.getElementById("symbol-input");
    if (!input) return;
    input.value = symbol;
    input.dispatchEvent(new Event("change"));
    /* A smooth scroll is an animation the visitor did not ask for, and the
       OS preference has to win over the page's taste. */
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.getElementById("live")?.scrollIntoView({
      behavior: reduced ? "auto" : "smooth",
      block: "start",
    });
  };

  document.getElementById("sc-body")?.addEventListener("click", (event) => {
    const symbol = event.target.closest("[data-symbol]")?.dataset?.symbol;
    if (!symbol) return;
    loadSymbol(symbol);
  });
}

async function boot() {
  try {
    const res = await fetch("data/screener.json");
    const data = await res.json();
    screenerRows = data.rows || [];
  } catch {
    screenerRows = [];
  }
  syncControls();
  render();
  wire();
}

boot();

})();
