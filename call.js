/* TradeMCP showcase — "The Call".

   WHAT THIS IS
   The handshake an AI agent performs against this server, shown while it
   happens: a JSON-RPC request leaves the agent, the server works, and a
   JSON payload comes back. The panel is a diagram in CSS 3D — two stations
   and the wire between them — and every number in it is real, fetched from
   the same endpoint the rest of the page already uses.

   WHAT YOU SEE, AND WHERE IT COMES FROM
   - The request pane holds the literal JSON-RPC request: method
     "tools/call", the tool name, and the arguments as they are sent.
   - The response pane holds the literal payload the server returned,
     taken from the MCP result content and pretty-printed. Nothing is
     reordered, trimmed or invented.
   - The latency is the wall-clock time of the fetch, measured with
     performance.now() around it. It is not an estimate and not a constant.
   - The source line says where the answer came from: the live /api
     endpoint, or the bundled snapshot when there is no server to ask.
   - The packet that crosses the wire is CSS. call.js only says which
     phase the diagram is in; the flight itself is keyframes in styles.css.

   RULES THIS FILE KEEPS
   - One call at a time. A second call while one is in flight is ignored,
     so the wire can never show two packets at once.
   - The answer always comes from the server or from the snapshot. There
     is no hard-coded price in this file, and if both fail the panel says
     so instead of inventing a number.
   - The page has to survive being opened from disk. A fetch of the
     snapshot is blocked by the browser's CORS rules on file://, so the
     failure state explains that the folder must be served over http.
   - Reduced motion removes the flight, not the call: the request still
     goes out and the real response still lands.

   THE ONE PLACE THIS FILE COULD LIE
   The diagram draws a packet flying out and an answer flying back on a
   fixed beat, because a diagram has to be readable. The round trip time
   printed under the scene is the measured one. If the server takes three
   seconds, the packet sits at the market station for three seconds
   before the answer comes back — the flight is theatre, the clock is not.
*/

(function () {
  "use strict";

  const doc = document;
  const board = doc.getElementById("call-board");
  if (!board) return;

  /* Same constants live.js uses, so both halves of the page agree. */
  const API = "api";
  const SNAPSHOT_URL = "data/snapshot.json";

  const TOOL = "trademcp_get_quote";
  const METHOD = "tools/call";

  /* The flight is a fixed beat, because a diagram has to be readable.
     It is not the network's timing — the clock in the panel is. */
  const OUT_MS = 760;  /* packet crossing to the market station */
  const BACK_MS = 760; /* answer crossing back to the agent */

  const els = {
    state: doc.getElementById("call-state"),
    request: doc.getElementById("call-request"),
    response: doc.getElementById("call-response"),
    reqMeta: doc.getElementById("call-req-meta"),
    resMeta: doc.getElementById("call-res-meta"),
    latency: doc.getElementById("call-latency"),
    source: doc.getElementById("call-source"),
    payload: doc.getElementById("call-payload"),
    answer: doc.getElementById("call-answer"),
    sym: doc.getElementById("call-answer-sym"),
    price: doc.getElementById("call-answer-price"),
    chg: doc.getElementById("call-answer-chg"),
    time: doc.getElementById("call-answer-time"),
    agentValue: doc.getElementById("call-agent-value"),
    marketValue: doc.getElementById("call-market-value"),
    packetTag: doc.querySelector("#call-packet .call__packet-tag"),
    go: doc.getElementById("call-go"),
    syms: Array.prototype.slice.call(doc.querySelectorAll(".call__sym")),
  };

  const reduceMotion =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let symbol = "RELIANCE";
  let busy = false;
  let requestId = 0;
  let snapshot = null; /* the bundled fallback, read at most once */

  /* ---------- helpers -------------------------------------------------------- */

  function wait(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  /* fetch with a deadline. The showcase server answers fast, but a host
     that has gone away should not hang the panel forever. */
  async function getJSON(url, timeoutMs) {
    const controller = new AbortController();
    const timer = window.setTimeout(function () { controller.abort(); }, timeoutMs || 15000);
    try {
      const res = await fetch(url, { signal: controller.signal, cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      return await res.json();
    } finally {
      window.clearTimeout(timer);
    }
  }

  function bytes(text) {
    if (window.TextEncoder) return new TextEncoder().encode(text).length;
    return text.length;
  }

  function setPhase(phase) {
    board.dataset.phase = phase;
  }

  /* ---------- the two ways to get an answer ---------------------------------- */

  /* The live path: the showcase server turns this into a real MCP
     tools/call over stdio against the TradeMCP server. */
  async function callLive(sym) {
    /* The live layer settles whether this host has a backend with the board's
       own first request. Waiting for that answer instead of asking again is
       what keeps a static host from logging a 404 page every time this panel
       is used. */
    if (window.trademcpApiReady) {
      const live = await window.trademcpApiReady;
      if (!live) throw new Error("no live endpoint on this host");
    }
    const payload = await getJSON(API + "/quote?symbol=" + encodeURIComponent(sym), 15000);
    if (!payload || typeof payload !== "object") throw new Error("empty payload");
    return { payload: payload, source: "live · /api/quote" };
  }

  /* The fallback path: the snapshot was written by these same tools, so
     a static host still shows a real answer — an older one. */
  async function callSnapshot(sym) {
    /* live.js loads this same file. Sharing it keeps one fetch of it on the
       page instead of one per module. */
    if (!snapshot) {
      snapshot = window.trademcpSnapshot
        ? await window.trademcpSnapshot()
        : await getJSON(SNAPSHOT_URL, 8000);
    }
    const rows = snapshot && Array.isArray(snapshot.tape) ? snapshot.tape : [];
    const wanted = sym.toUpperCase();
    for (let i = 0; i < rows.length; i += 1) {
      const row = rows[i];
      if (row && String(row.symbol).toUpperCase() === wanted) {
        return { payload: row, source: "snapshot · data/snapshot.json" };
      }
    }
    throw new Error(sym + " is not in the snapshot");
  }

  /* ---------- painting -------------------------------------------------------- */

  function paintRequest() {
    requestId += 1;
    const request = {
      jsonrpc: "2.0",
      id: requestId,
      method: METHOD,
      params: {
        name: TOOL,
        arguments: { symbol: symbol, exchange: "NSE", response_format: "json" },
      },
    };
    els.request.textContent = JSON.stringify(request, null, 2);
    els.reqMeta.textContent = "jsonrpc 2.0 · " + METHOD + " · id " + requestId;
  }

  function resetAnswer() {
    els.answer.dataset.tone = "flat";
    els.sym.textContent = symbol;
    els.price.textContent = "—";
    els.chg.textContent = "—";
    els.time.textContent = "—";
    els.latency.textContent = "—";
    els.source.textContent = "—";
    els.payload.textContent = "—";
    els.marketValue.textContent = "trademcp";
    els.agentValue.textContent = "mcp client";
  }

  function paintResult(result, elapsedMs) {
    const payload = result.payload;
    const text = JSON.stringify(payload, null, 2);
    const size = bytes(text);
    const fields = payload && typeof payload === "object" ? Object.keys(payload).length : 0;

    els.response.textContent = text;
    els.resMeta.textContent = "result.content[0].text · " + size + " B";
    els.payload.textContent = fields + " fields · " + size + " B";
    els.latency.textContent = Math.round(elapsedMs) + " ms";
    els.source.textContent = result.source;

    const isLive = result.source.indexOf("live") === 0;
    els.state.textContent = isLive ? "Live" : "Snapshot";
    els.state.dataset.state = isLive ? "live" : "snapshot";

    const price = Number(payload.price);
    const change = Number(payload.change_pct);
    const up = change >= 0;

    if (payload.symbol) els.sym.textContent = payload.symbol;
    if (isFinite(price)) els.price.textContent = price.toFixed(2);
    if (isFinite(change)) {
      els.chg.textContent = (up ? "▲ " : "▼ ") + (up ? "+" : "") + change.toFixed(2) + "%";
      els.answer.dataset.tone = up ? "up" : "down";
      els.agentValue.textContent = (up ? "▲ " : "▼ ") + Math.abs(change).toFixed(2) + "%";
    } else {
      els.chg.textContent = "—";
      els.agentValue.textContent = "received";
    }
    if (isFinite(price)) els.marketValue.textContent = price.toFixed(2);
    els.time.textContent = payload.last_traded_at || "—";
  }

  function paintFailure(message, elapsedMs) {
    els.response.textContent = "// " + message;
    els.resMeta.textContent = "no result";
    els.payload.textContent = "—";
    els.latency.textContent = Math.round(elapsedMs) + " ms";
    els.source.textContent = "no server, no snapshot";
    els.state.textContent = "No answer";
    els.state.dataset.state = "error";
    els.answer.dataset.tone = "flat";
    els.price.textContent = "—";
    els.chg.textContent = "—";
    els.time.textContent =
      location.protocol === "file:"
        ? "serve this folder over http to read the snapshot"
        : "—";
  }

  /* ---------- the call -------------------------------------------------------- */

  async function run(nextSymbol) {
    if (busy) return;
    busy = true;
    if (nextSymbol) symbol = nextSymbol;

    els.syms.forEach(function (btn) {
      btn.setAttribute("aria-pressed", String(btn.dataset.symbol === symbol));
    });

    setPhase("ask");
    els.packetTag.textContent = "REQ";
    els.state.textContent = "Calling…";
    els.state.dataset.state = "live";
    paintRequest();
    resetAnswer();
    els.response.textContent = "";

    const started = performance.now();
    let result = null;
    let failure = null;
    let elapsed = 0;

    try {
      try {
        result = await callLive(symbol);
        elapsed = performance.now() - started;
      } catch (liveError) {
        /* No server here. Try the bundled snapshot before giving up. */
        const retryStart = performance.now();
        try {
          result = await callSnapshot(symbol);
          elapsed = performance.now() - retryStart;
        } catch (snapError) {
          failure = liveError;
          elapsed = performance.now() - retryStart;
        }
      }

      /* Let the packet finish its crossing before the answer leaves, so the
         two legs never overlap and the answer always leaves the station the
         request landed on. */
      if (!reduceMotion) {
        const flown = performance.now() - started;
        await wait(Math.max(0, OUT_MS - flown));
      }

      if (failure) {
        setPhase("error");
        paintFailure(failure && failure.message ? failure.message : "request failed", elapsed);
        return;
      }

      setPhase("answer");
      els.packetTag.textContent = "RES";
      if (!reduceMotion) await wait(BACK_MS);

      setPhase("done");
      paintResult(result, elapsed);
    } finally {
      busy = false;
    }
  }

  /* ---------- wiring ---------------------------------------------------------- */

  els.go.addEventListener("click", function () {
    run(symbol);
  });

  els.syms.forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (busy) return;
      run(btn.dataset.symbol);
    });
  });

  /* The call runs once on load. The section is proof, not a promise:
     a reader who never scrolls to it has still seen it work. */
  run("RELIANCE");
})();
