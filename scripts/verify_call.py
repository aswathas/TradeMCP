"""Verify THE CALL holds together: the handshake, the fallback, the 3D, and
the page it left behind.

THE CALL is the one section of the page that shows an agent talking to the
server. Two things about it are easy to get wrong and invisible in a unit
test:

  1. The request and the response panes are supposed to hold REAL data. A
     pretty-printed sample would look exactly the same in a screenshot, and
     the page would go on claiming to be proof rather than a mock.
  2. The 3D diagram is a diagram, not a rendering. The packet has to cross
     the wire, the answer has to come back, and the number that lands has to
     be the number that was fetched.

So this drives the real page in headless Chrome through a true-width iframe
(Chrome refuses a window narrower than 500px, so --window-size lies about
phones) and asserts:

  1. no horizontal overflow at 320 / 360 / 390 / 1440, in every theme
  2. the request pane is a real JSON-RPC tools/call request
  3. the response pane parses as JSON and carries a price
  4. the latency is a measured number, not a placeholder
  5. with /api/quote blocked, the panel falls back to the bundled snapshot
  6. the page loads nothing from a CDN - the roster's Three.js is gone and
     the folder is static again
  7. the roster is really gone: no section, no script, no library
  8. the custom cursor still hands over and still gives the native arrow back

    python scripts/verify_call.py --port 8099
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

SITE = Path(__file__).resolve().parent.parent / "showcase" / "site"

WIDTHS = (320, 360, 390, 1440)
THEMES = ("paper", "night", "void", "shrine")

# How long the wrapper waits before it reads the page. The call itself is a
# 760ms beat out, a 760ms beat back, plus the round trip to the server.
WAIT_MS = 7000

WRAPPER = """<!doctype html>
<meta charset="utf-8">
<title>probe</title>
<style>
  html, body {{ margin: 0; padding: 0; background: #000; overflow: hidden; }}
  iframe {{ display: block; border: 0; width: {w}px; height: {h}px; }}
</style>
<iframe src="http://127.0.0.1:{port}/index.html{query}"></iframe>
<script>
window.onerror = (m) => {{ document.title = "ERR(" + m + ")"; }};
setTimeout(() => {{
  try {{
    const frame = document.querySelector("iframe");
    const d = frame.contentDocument;
    const w = frame.contentWindow;
    const out = {{}};

    const text = (id) => {{
      const el = d.getElementById(id);
      return el ? el.textContent.trim() : null;
    }};

    /* ---- 1. the layout, in every theme ------------------------------- */
    for (const theme of {themes}) {{
      d.documentElement.dataset.theme = theme;
      const board = d.getElementById("call-board");
      const scene = d.getElementById("call-scene");
      const agent = d.querySelector(".call__station--agent");
      const market = d.querySelector(".call__station--market");
      const face = d.querySelector(".call__face");
      const top = d.querySelector(".call__node-top");
      const side = d.querySelector(".call__node-side");
      const wire = d.querySelector(".call__wire");
      const rect = (el) => {{
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return {{ x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width),
                  h: Math.round(r.height) }};
      }};
      out[theme] = {{
        scrollW: d.documentElement.scrollWidth,
        clientW: d.documentElement.clientWidth,
        board: rect(board),
        scene: rect(scene),
        agent: rect(agent),
        market: rect(market),
        face: rect(face),
        top: rect(top),
        side: rect(side),
        wire: rect(wire),
        topTransform: top ? getComputedStyle(top).transform : null,
        sideTransform: side ? getComputedStyle(side).transform : null,
        scenePerspective: scene ? getComputedStyle(scene).perspective : null,
      }};
    }}

    /* ---- 2. the handshake --------------------------------------------- */
    d.documentElement.dataset.theme = "paper";
    out.call = {{
      phase: d.getElementById("call-board").dataset.phase,
      state: text("call-state"),
      request: text("call-request"),
      response: text("call-response"),
      latency: text("call-latency"),
      source: text("call-source"),
      payload: text("call-payload"),
      sym: text("call-answer-sym"),
      price: text("call-answer-price"),
      chg: text("call-answer-chg"),
      time: text("call-answer-time"),
      agentValue: text("call-agent-value"),
      marketValue: text("call-market-value"),
      resMeta: text("call-res-meta"),
    }};

    /* ---- 3. the roster is really gone --------------------------------- */
    out.roster = {{
      section: d.querySelectorAll("#roster").length,
      nav: d.querySelectorAll('a[href="#roster"]').length,
      scripts: Array.from(d.querySelectorAll("script[src]"))
        .map((s) => s.getAttribute("src"))
        .filter((s) => /roster|three/i.test(s)),
      canvases: d.querySelectorAll("canvas").length,
    }};

    /* ---- 4. nothing comes from a CDN ----------------------------------- */
    out.resources = performance.getEntriesByType("resource")
      .map((r) => r.name)
      .filter((n) => n.indexOf("127.0.0.1") === -1 && n.indexOf("localhost") === -1);
    out.frameResources = w.performance.getEntriesByType("resource")
      .map((r) => r.name)
      .filter((n) => n.indexOf("127.0.0.1") === -1 && n.indexOf("localhost") === -1);

    /* ---- 5. the cursor still hands over -------------------------------- */
    const beforeMove = d.documentElement.classList.contains("has-cursor");
    d.dispatchEvent(new w.PointerEvent("pointermove", {{
      clientX: 120, clientY: 120, bubbles: true,
    }}));
    out.cursor = {{
      beforeMove: beforeMove,
      afterMove: d.documentElement.classList.contains("has-cursor"),
      mark: d.querySelectorAll(".cursor").length,
    }};

    /* ---- 6. the fallback: block /api/quote, keep the snapshot --------- */
    const realFetch = w.fetch;
    w.fetch = function (url, opts) {{
      if (String(url).indexOf("api/quote") !== -1) {{
        return Promise.reject(new Error("blocked by the test"));
      }}
      return realFetch(url, opts);
    }};
    d.getElementById("call-go").click();

    /* ---- 7. the anchor lands below the sticky masthead ------------------ */
    const masthead = d.querySelector(".masthead");
    const call = d.getElementById("call");
    const mRect = masthead.getBoundingClientRect();
    const cRect = call.getBoundingClientRect();
    out.anchor = {{
      mastheadBottom: Math.round(mRect.bottom),
      callTop: Math.round(cRect.top),
      clear: Math.round(cRect.top - mRect.bottom),
    }};

    setTimeout(() => {{
      out.fallback = {{
        phase: d.getElementById("call-board").dataset.phase,
        state: text("call-state"),
        source: text("call-source"),
        response: text("call-response"),
        latency: text("call-latency"),
        price: text("call-answer-price"),
      }};
      document.title = "RESULT" + JSON.stringify(out);
    }}, 4000);
  }} catch (e) {{ document.title = "ERR(" + e.message + ")"; }}
}}, {wait});
</script>
"""


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("google-chrome") or shutil.which("chromium")
    if not found:
        raise SystemExit("No Chrome or Chromium found.")
    return found


def probe(chrome: str, port: int, width: int, query: str = "") -> dict:
    wrapper = SITE / "_verify.html"
    wrapper.write_text(
        WRAPPER.format(
            w=width,
            h=1400,
            port=port,
            query=query,
            wait=WAIT_MS,
            themes=json.dumps(list(THEMES)),
        ),
        encoding="utf-8",
    )
    try:
        with tempfile.TemporaryDirectory() as tmp:
            res = subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--no-first-run", "--no-default-browser-check",
                 f"--user-data-dir={tmp}", f"--window-size={max(width + 20, 500)},1400",
                 "--virtual-time-budget=30000", "--dump-dom",
                 f"http://127.0.0.1:{port}/_verify.html"],
                capture_output=True, timeout=260,
            )
    finally:
        wrapper.unlink(missing_ok=True)

    out = res.stdout.decode("utf-8", "replace")
    m = re.search(r"<title>(RESULT|ERR)(.*?)</title>", out, re.S)
    if not m:
        raise SystemExit(f"no probe result at {width}px:\n{out[-600:]}")
    if m.group(1) == "ERR":
        raise SystemExit(f"probe error at {width}px: {m.group(2)}")
    return json.loads(m.group(2))


def main() -> int:
    # The page prints arrows and middle dots; a cp1252 console cannot.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()
    chrome = find_chrome()

    failures: list[str] = []

    # ------------------------------------------------------------------ 1
    print("== layout: no overflow, and the 3D is really 3D ==")
    data = probe(chrome, args.port, 1440)
    for theme in THEMES:
        info = data[theme]
        overflow = info["scrollW"] - info["clientW"]
        ok = overflow <= 0
        # the two stations must sit at the two ends of the scene and not overlap
        agent, market = info["agent"], info["market"]
        apart = bool(agent and market and market["x"] > agent["x"])
        # the slab must have a lit top plane and a shaded side plane, or the
        # thing on the page is a flat rectangle pretending to be 3D
        has_top = bool(info["topTransform"] and info["topTransform"] != "none")
        has_side = bool(info["sideTransform"] and info["sideTransform"] != "none")
        ok = ok and apart and has_top and has_side
        print(
            f"  {'ok ' if ok else 'FAIL'} {theme:<7} overflow={overflow:>3}px"
            f"  agent_x={agent['x'] if agent else '?'} market_x={market['x'] if market else '?'}"
            f"  top={has_top} side={has_side}"
        )
        if not ok:
            failures.append(
                f"{theme}: overflow={overflow} apart={apart} top={has_top} side={has_side}"
            )

    # ------------------------------------------------------------------ 2
    print("\n== the handshake ==")
    call = data.get("call") or {}
    phase = call.get("phase")
    ok_phase = phase == "done"
    print(f"  {'ok ' if ok_phase else 'FAIL'} phase={phase}")
    if not ok_phase:
        failures.append(f"the call never finished: phase={phase}")

    req = call.get("request") or ""
    try:
        req_json = json.loads(req)
    except Exception:
        req_json = {}
    ok_req = (
        req_json.get("jsonrpc") == "2.0"
        and req_json.get("method") == "tools/call"
        and req_json.get("params", {}).get("name") == "trademcp_get_quote"
        and req_json.get("params", {}).get("arguments", {}).get("symbol")
    )
    print(
        f"  {'ok ' if ok_req else 'FAIL'} request is a real JSON-RPC tools/call"
        f" ({req_json.get('method')} / {req_json.get('params', {}).get('name')})"
    )
    if not ok_req:
        failures.append(f"the request pane is not a tools/call request: {req[:160]}")

    res = call.get("response") or ""
    try:
        res_json = json.loads(res)
    except Exception:
        res_json = {}
    ok_res = isinstance(res_json, dict) and "price" in res_json and "symbol" in res_json
    print(
        f"  {'ok ' if ok_res else 'FAIL'} response parses and carries a price"
        f" (symbol={res_json.get('symbol') if res_json else '?'}"
        f" price={res_json.get('price') if res_json else '?'})"
    )
    if not ok_res:
        failures.append(f"the response pane is not a quote payload: {res[:160]}")

    lat = call.get("latency") or ""
    ok_lat = bool(re.fullmatch(r"\d+ ms", lat))
    print(f"  {'ok ' if ok_lat else 'FAIL'} latency is a measured number ({lat})")
    if not ok_lat:
        failures.append(f"latency is not a number of milliseconds: {lat!r}")

    src = call.get("source") or ""
    ok_src = src.startswith("live") or src.startswith("snapshot")
    print(f"  {'ok ' if ok_src else 'FAIL'} source says where it came from ({src})")
    if not ok_src:
        failures.append(f"the source line does not say live or snapshot: {src!r}")

    ok_price = bool(call.get("price") and call["price"] != "—")
    print(f"  {'ok ' if ok_price else 'FAIL'} the answer strip shows the price ({call.get('price')})")
    if not ok_price:
        failures.append("the answer strip has no price")

    # green up / red down, always with an arrow
    chg = call.get("chg") or ""
    ok_chg = ("▲" in chg or "▼" in chg) or chg == "—"
    print(f"  {'ok ' if ok_chg else 'FAIL'} the change carries an arrow ({chg})")
    if not ok_chg:
        failures.append(f"the change has no arrow: {chg!r}")

    # ------------------------------------------------------------------ 3
    print("\n== the fallback: /api/quote blocked ==")
    fb = data.get("fallback") or {}
    ok_fb = (
        fb.get("source") == "snapshot · data/snapshot.json"
        and fb.get("phase") == "done"
        and fb.get("price")
        and fb.get("price") != "—"
    )
    print(
        f"  {'ok ' if ok_fb else 'FAIL'} source={fb.get('source')} phase={fb.get('phase')}"
        f" price={fb.get('price')}"
    )
    if not ok_fb:
        failures.append(f"the snapshot fallback did not take over: {fb}")

    # ------------------------------------------------------------------ 4
    print("\n== nothing comes from a CDN ==")
    third_party = list(data.get("resources") or []) + list(data.get("frameResources") or [])
    # Google Fonts is the one thing the page has always fetched.
    fonts = [u for u in third_party if "fonts.g" in u]
    others = [u for u in third_party if "fonts.g" not in u]
    ok_cdn = not others
    print(f"  {'ok ' if ok_cdn else 'FAIL'} third-party requests: {others or 'none'}")
    print(f"       (fonts, as always: {len(fonts)})")
    if not ok_cdn:
        failures.append(f"the page reaches a third party: {others}")

    # ------------------------------------------------------------------ 5
    print("\n== the roster is gone ==")
    roster = data.get("roster") or {}
    ok_roster = (
        roster.get("section") == 0
        and roster.get("nav") == 0
        and not roster.get("scripts")
    )
    print(
        f"  {'ok ' if ok_roster else 'FAIL'} section={roster.get('section')}"
        f" nav={roster.get('nav')} scripts={roster.get('scripts')}"
    )
    if not ok_roster:
        failures.append(f"the roster is still on the page: {roster}")

    # ------------------------------------------------------------------ 6
    print("\n== the cursor still hands over ==")
    cur = data.get("cursor") or {}
    ok_cur = cur.get("beforeMove") is False and cur.get("afterMove") is True and cur.get("mark") == 1
    print(
        f"  {'ok ' if ok_cur else 'FAIL'} native arrow before the first move="
        f"{cur.get('beforeMove')} after={cur.get('afterMove')} marks={cur.get('mark')}"
    )
    if not ok_cur:
        failures.append(f"the cursor does not hand over cleanly: {cur}")

    sysdata = probe(chrome, args.port, 1440, query="?cursor=system")
    syscur = sysdata.get("cursor") or {}
    ok_sys = syscur.get("afterMove") is False and syscur.get("mark") == 0
    print(f"  {'ok ' if ok_sys else 'FAIL'} ?cursor=system keeps the native arrow")
    if not ok_sys:
        failures.append(f"?cursor=system did not give the native arrow back: {syscur}")

    # ------------------------------------------------------------------ 7
    print("\n== every width, no overflow ==")
    for width in WIDTHS:
        wdata = probe(chrome, args.port, width)
        for theme in THEMES:
            info = wdata[theme]
            overflow = info["scrollW"] - info["clientW"]
            ok = overflow <= 0
            print(f"  {'ok ' if ok else 'FAIL'} {width:>4}px {theme:<7} overflow={overflow:>3}px")
            if not ok:
                failures.append(f"{width}px {theme}: overflow={overflow}px")

    # ------------------------------------------------------------------ 8
    print("\n== the anchor lands below the sticky masthead ==")
    for width in (390, 1440):
        anchordata = probe(chrome, args.port, width, query="#call")
        anc = anchordata.get("anchor") or {}
        clear = anc.get("clear", -999)
        ok_anchor = clear >= 0
        print(
            f"  {'ok ' if ok_anchor else 'FAIL'} {width:>4}px: masthead ends at"
            f" {anc.get('mastheadBottom')}, section starts at {anc.get('callTop')}"
            f" (clear {clear}px)"
        )
        if not ok_anchor:
            failures.append(f"{width}px: the #call anchor lands under the masthead: {anc}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nAll call checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
