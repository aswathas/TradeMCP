/* TradeMCP showcase — interaction layer.
   Vanilla JS, no build step. Renders the metric chips from the same lists the
   server uses, wires the copy buttons, the theme toggle and the tool cards. */

const CHIP_GROUPS = {
  trend: {
    label: "Trend · 25",
    items: [
      "sma_20", "sma_50", "sma_200", "ema_9", "ema_21", "ema_50", "ema_200",
      "macd", "macd_signal", "macd_histogram", "adx_14", "plus_di", "minus_di",
      "supertrend", "parabolic_sar", "ichimoku_tenkan", "ichimoku_kijun",
      "ichimoku_senkou_a", "ichimoku_senkou_b", "aroon_up", "aroon_down",
      "vortex_plus", "vortex_minus", "linear_slope_20",
    ],
  },
  momentum: {
    label: "Momentum · 13",
    items: [
      "rsi_7", "rsi_14", "stochastic_k", "stochastic_d", "stoch_rsi_k",
      "cci_20", "williams_r", "mfi_14", "roc_10", "cmo_14", "tsi",
      "ultimate_oscillator", "awesome_oscillator",
    ],
  },
  volatility: {
    label: "Volatility · 12",
    items: [
      "atr_14", "true_range", "bollinger_upper", "bollinger_middle",
      "bollinger_lower", "bollinger_percent_b", "bollinger_bandwidth",
      "keltner_upper", "keltner_lower", "donchian_upper", "donchian_lower",
      "historical_volatility", "zscore_20",
    ],
  },
  volume: {
    label: "Volume · 7",
    items: [
      "obv", "vwap", "chaikin_money_flow", "accumulation_distribution",
      "price_volume_trend", "force_index", "volume_ratio_20",
    ],
  },
  valuation: {
    label: "Valuation · 12",
    items: [
      "P/E", "PEG", "P/B", "P/S", "EV/EBITDA", "EV/Sales", "market cap",
      "enterprise value", "dividend yield", "EPS", "book value/share", "DPS",
    ],
  },
  profitability: {
    label: "Profitability · 11",
    items: [
      "gross margin", "operating margin", "EBITDA margin", "net margin", "ROE",
      "ROA", "ROCE", "ROIC", "asset turnover", "equity multiplier",
      "effective tax rate",
    ],
  },
  leverage: {
    label: "Leverage · 7",
    items: [
      "debt/equity", "debt/assets", "cash", "net debt", "net debt/EBITDA",
      "interest coverage", "debt/capital",
    ],
  },
  liquidity: {
    label: "Liquidity · 12",
    items: [
      "current ratio", "quick ratio", "cash ratio", "working capital",
      "working capital/share", "operating cash flow", "free cash flow",
      "FCF margin", "CFO/net income", "capex", "CFPS", "FCFPS",
    ],
  },
  growth: {
    label: "Growth · 8",
    items: [
      "revenue YoY", "net income YoY", "EPS YoY", "CFO YoY",
      "revenue 3y CAGR", "revenue 5y CAGR", "net income 3y CAGR",
      "net income 5y CAGR",
    ],
  },
  dupont: {
    label: "DuPont · 4",
    items: [
      "net margin", "asset turnover", "equity multiplier", "reconciled ROE",
    ],
  },
};

function renderChips() {
  document.querySelectorAll("[data-chips]").forEach((host) => {
    const group = CHIP_GROUPS[host.dataset.chips];
    if (!group) return;

    const label = document.createElement("span");
    label.className = "chip__group";
    label.textContent = group.label;
    host.appendChild(label);

    for (const item of group.items) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = item;
      host.appendChild(chip);
    }
  });
}

function toast(message) {
  const node = document.getElementById("toast");
  if (!node) return;
  node.textContent = message;
  node.classList.add("is-on");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => node.classList.remove("is-on"), 2600);
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for pages opened from file:// where the clipboard API is blocked.
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    document.body.removeChild(area);
    return ok;
  }
}

/* The install path is one npx command. The hero button hands the visitor that
   command as a file, so it can be pasted or run as it is. */
const NPX_COMMAND = "npx -y @aswathas/trademcp";

function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function npxCommandFile() {
  return [
    "# TradeMCP - free MCP server for Indian equities (NSE/BSE)",
    "# 14 tools, 57 technical indicators, 54 fundamental ratios, a screener.",
    "# No API key, no account. Node 18+ and Python 3.11+ are the only requirements.",
    "",
    "# 1. add it to your MCP client",
    NPX_COMMAND,
    "",
    "# 2. or install it once, if your client has a short start-up timeout",
    "npm i -g @aswathas/trademcp",
    "#    then use \"trademcp\" as the command",
    "",
    "# 3. Claude Desktop, Cursor, Windsurf, VS Code  (mcpServers block)",
    "{",
    '  "mcpServers": {',
    '    "trademcp": {',
    '      "command": "npx",',
    '      "args": ["-y", "@aswathas/trademcp"]',
    "    }",
    "  }",
    "}",
    "",
    "# 4. Claude Code",
    "claude mcp add trademcp -- npx -y @aswathas/trademcp",
    "",
    "# Source: https://github.com/aswathas/TradeMCP",
    "",
  ].join("\n");
}

function wireNpxDownload() {
  const button = document.getElementById("npx-cta");
  if (!button) return;
  button.addEventListener("click", () => {
    downloadText("trademcp-npx.txt", npxCommandFile());
    toast("Downloaded — run the command in your MCP client");
  });
}

function wireCopyButtons() {
  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.getElementById(button.dataset.copyTarget);
      if (!target) return;
      const ok = await copyText(target.textContent.trim());
      toast(ok ? "Copied — paste it into your client" : "Copy failed — select it manually");
    });
  });
}

/* ---------- theme and cursed domain --------------------------------------
   Two whole-page domains: the Infinite Void and the Malevolent Shrine.
   The attacks (Blue attracts, Red repels) are components inside the page,
   not themes. Only paper and night are ever written to storage.
   ------------------------------------------------------------------------ */

const domainState = { base: "paper", active: null };

const domainButtons = {
  void: [document.getElementById("domain-btn"), document.getElementById("domain-void")],
  shrine: [document.getElementById("tech-shrine"), document.getElementById("domain-shrine")],
};

const domainLabels = {
  void: "Infinite Void",
  shrine: "Malevolent Shrine",
};

function paintTheme(theme) {
  const button = document.getElementById("theme-toggle");
  document.documentElement.dataset.theme = theme;
  const night = theme === "night";
  if (!button) return;
  button.setAttribute("aria-pressed", String(night));
  const text = button.querySelector(".theme-toggle__text");
  const glyph = button.querySelector(".theme-toggle__glyph");
  if (text) text.textContent = night ? "Paper" : "Night";
  if (glyph) glyph.textContent = night ? "◑" : "◐";
  // The call to action carries the domain's own technique.
  const fuga = document.getElementById("fuga-label");
  if (fuga) {
    fuga.textContent =
      theme === "shrine"
        ? "Fūga / Open Furnace"
        : theme === "void"
          ? "Cleave / pull data"
          : "Refresh the feed";
  }
}

function paintDomain() {
  for (const key of Object.keys(domainButtons)) {
    for (const button of domainButtons[key]) {
      if (!button) continue;
      const on = domainState.active === key;
      button.setAttribute("aria-pressed", String(on));
      const sub = button.querySelector(".tech__sub");
      if (sub) sub.textContent = on ? "Collapse the domain" : domainLabels[key];
    }
  }
}

/* Dismantle: a single cut across the page when a domain lets go. */
function slash() {
  const root = document.documentElement;
  root.classList.remove("is-cut");
  // Re-adding the class on the next frame restarts the animation.
  void root.offsetWidth;
  root.classList.add("is-cut");
  clearTimeout(slash._timer);
  slash._timer = setTimeout(() => root.classList.remove("is-cut"), 700);
}

/* Press a domain to open it. Press it again to let it go. */
let lastCast = 0;
let lastCastKey = "";
function castDomain(key) {
  // A double-tap on the SAME button would open it and then instantly close
  // it, which reads as a broken button — so only the first tap of a pair
  // counts. A tap on a DIFFERENT button always works: switching straight
  // from Void to Shrine must never be swallowed, because a thumb that taps
  // fast is not double-tapping.
  const now = Date.now();
  if (key === lastCastKey && now - lastCast < 350) return;
  lastCast = now;
  lastCastKey = key;
  if (domainState.active === key) {
    domainState.active = null;
    paintTheme(domainState.base);
    slash();
  } else {
    domainState.active = key;
    paintTheme(key);
  }
  paintDomain();
}

function wireThemeToggle() {
  const button = document.getElementById("theme-toggle");
  const stored = localStorage.getItem("trademcp-theme");
  // The direction is a printed manga page, so paper is the default even when
  // the OS asks for dark. Night stays one click away.
  domainState.base = stored === "night" ? "night" : "paper";

  // ?theme=void|shrine|night|paper opens the page in that domain, so a link
  // can share exactly what the reader is looking at.
  const wanted = new URLSearchParams(location.search).get("theme");
  if (wanted === "void" || wanted === "shrine") {
    domainState.active = wanted;
    paintTheme(wanted);
  } else if (wanted === "night" || wanted === "paper") {
    domainState.base = wanted;
    paintTheme(wanted);
  } else {
    paintTheme(domainState.base);
  }

  if (!button) return;
  button.addEventListener("click", () => {
    domainState.active = null;
    domainState.base = domainState.base === "paper" ? "night" : "paper";
    paintTheme(domainState.base);
    paintDomain();
    localStorage.setItem("trademcp-theme", domainState.base);
  });
}

function wireDomains() {
  for (const key of Object.keys(domainButtons)) {
    for (const button of domainButtons[key]) {
      if (!button) continue;
      button.addEventListener("click", () => castDomain(key));
    }
  }
  paintDomain();
}

/* Fūga (shrine) and Blue Lapse (void) both do the same honest thing: they
   re-pull the live feed from the MCP server and flash the domain's colour. */
function wireFuga() {
  const button = document.getElementById("fuga-btn");
  if (!button) return;
  button.addEventListener("click", () => {
    const root = document.documentElement;
    root.classList.remove("is-cast");
    // Re-adding the class on the next frame restarts the animation.
    void root.offsetWidth;
    root.classList.add("is-cast");
    clearTimeout(wireFuga._timer);
    wireFuga._timer = setTimeout(() => root.classList.remove("is-cast"), 900);

    const refresh = document.getElementById("board-refresh");
    if (refresh) refresh.click();
    const theme = root.dataset.theme;
    toast(
      theme === "shrine"
        ? "Feed re-initialized · Divine Flame"
        : theme === "void"
          ? "Feed pulled in · Blue Lapse"
          : "Feed refreshed"
    );
  });
}

/* Dismantle: tear the cursed domain down and let the base theme back in.
   The cut is the same slash a domain makes when it lets go. */
function wireDismantle() {
  const button = document.getElementById("dismantle-btn");
  if (!button) return;
  button.addEventListener("click", () => {
    const was = domainState.active;
    domainState.active = null;
    paintTheme(domainState.base);
    paintDomain();
    slash();
    toast(was ? "Domain dismantled · back to the base page" : "No domain open · nothing to tear down");
  });
}

function wireToolCards() {
  document.querySelectorAll(".tool").forEach((card) => {
    const summary = card.querySelector("summary");
    if (!summary) return;
    summary.addEventListener("click", () => {
      // One card open at a time keeps the grid legible.
      if (card.open) return;
      document.querySelectorAll(".tool[open]").forEach((other) => {
        if (other !== card) other.removeAttribute("open");
      });
    });
  });
}

/* ---------- 3D: pointer tilt and scroll dolly ---------------------------- */

function wireTilt() {
  /* The two hero planes do not tilt. They are full-height walls, and rotating
     them toward the pointer used to push their top edge behind the roof that
     used to hang over them, so moving the cursor near the first box made the
     box disappear under the eaves. The roof is gone now, but the rule stays:
     the hero boxes are the page, and the small cards below keep the tilt. */
  const cards = document.querySelectorAll(
    ".panel--metrics, .metric-panel, .tool, .step, .source, .sc-table"
  );
  const MAX = 3.5;
  /* One media query, read once, not on every pointermove. */
  const still = window.matchMedia("(prefers-reduced-motion: reduce)");

  const reset = (card) => {
    card.classList.remove("tilt");
    card.style.setProperty("--tilt-y", "0deg");
    card.style.setProperty("--tilt-x", "0deg");
  };

  cards.forEach((card) => {
    /* The rect read is a forced layout, and pointermove fires sixty times a
       second across forty cards. Reading it inside a rAF, once per frame,
       is the same trick wireDolly already uses. */
    let queued = false;
    let px = 0;
    let py = 0;

    const apply = () => {
      queued = false;
      if (still.matches) return;
      const rect = card.getBoundingClientRect();
      const x = (px - rect.left) / rect.width - 0.5;
      const y = (py - rect.top) / rect.height - 0.5;
      card.classList.add("tilt");
      card.style.setProperty("--tilt-y", `${(x * MAX).toFixed(2)}deg`);
      card.style.setProperty("--tilt-x", `${(-y * MAX).toFixed(2)}deg`);
    };

    card.addEventListener("pointermove", (event) => {
      if (still.matches) return;
      px = event.clientX;
      py = event.clientY;
      if (queued) return;
      queued = true;
      requestAnimationFrame(apply);
    });

    /* A touch gesture that becomes a scroll cancels the pointer, and the
       card would keep the skew it had when the finger lifted. */
    card.addEventListener("pointerleave", () => reset(card));
    card.addEventListener("pointercancel", () => reset(card));
    card.addEventListener("pointerup", () => reset(card));
  });
}

function wireDolly() {
  const root = document.documentElement;
  let queued = false;

  const update = () => {
    queued = false;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      root.style.setProperty("--dolly", "0");
      return;
    }
    const height = window.innerHeight || 1;
    const progress = Math.min(window.scrollY / height, 1);
    root.style.setProperty("--dolly", progress.toFixed(3));
  };

  window.addEventListener(
    "scroll",
    () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(update);
    },
    { passive: true }
  );
  update();
}

renderChips();
wireCopyButtons();
wireNpxDownload();
wireThemeToggle();
wireDomains();
wireFuga();
wireDismantle();
wireToolCards();
wireTilt();
wireDolly();

// ?flat=1 flattens the 3D planes for still capture. Composited layers do not
// paint reliably in headless screenshots, so the stills ask for a flat page.
if (new URLSearchParams(location.search).get("flat") === "1") {
  document.documentElement.classList.add("is-flat");
}

// A deep link to a section can land before the live data has resized the
// page, which leaves the reader in the wrong place. Re-seat it as the
// document settles.
window.addEventListener("load", () => {
  if (!location.hash) return;
  const seat = () => {
    const target = document.querySelector(location.hash);
    if (target) target.scrollIntoView();
  };
  seat();
  setTimeout(seat, 250);
  setTimeout(seat, 2500);
});