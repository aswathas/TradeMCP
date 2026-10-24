"""Verify the shrine upgrade holds together in every theme, at every width.

The shrine upgrade added real art to the page (a roof, a maw, a neon frame)
and each piece is scoped to the shrine theme. Art that leaks into another
domain paints over the copy, and art that leaks past the viewport makes the
page scroll sideways on a phone - neither shows up in a unit test.

So this drives the real page in headless Chrome through a true-width iframe
(Chrome refuses a window narrower than 500px, so --window-size lies about
phones) and asserts:

  1. no horizontal overflow at 320 / 360 / 390 / 1440, in every theme
  2. the shrine plates paint in the shrine and nowhere else
  3. the domain switch still changes the theme and keeps its aria-pressed state

    python scripts/verify_shrine.py --port 8099

The script serves the site itself: the probe page and the site have to be on
the same origin for the iframe to be readable, and a check that needs a server
the reader forgot to start is a check that silently never runs.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
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

WRAPPER = """<!doctype html>
<meta charset="utf-8">
<title>probe</title>
<style>
  html, body {{ margin: 0; padding: 0; background: #000; overflow: hidden; }}
  iframe {{ display: block; border: 0; width: {w}px; height: {h}px; }}
</style>
<iframe src="http://127.0.0.1:{port}/index.html?theme=paper"></iframe>
<script>
window.onerror = (m) => {{ document.title = "ERR(" + m + ")"; }};
setTimeout(() => {{
  try {{
    const d = document.querySelector("iframe").contentDocument;
    const out = {{}};
    for (const theme of {themes}) {{
      d.documentElement.dataset.theme = theme;
      const plates = Array.from(d.querySelectorAll(".shrine-fangs"))
        .map((el) => {{
          const cs = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return {{ display: cs.display, w: Math.round(r.width), h: Math.round(r.height) }};
        }});
      // the neon plate is the border of the Fuga button now, not of the panel
      const flame = d.querySelector(".btn__flame");
      const hero = d.querySelector(".panel--hero").getBoundingClientRect();
      const hud = d.querySelector(".panel--hud").getBoundingClientRect();
      out[theme] = {{
        scrollW: d.documentElement.scrollWidth,
        clientW: d.documentElement.clientWidth,
        plates: plates,
        flameOn: flame ? getComputedStyle(flame).display !== "none" : false,
        heroH: Math.round(hero.height),
        hudH: Math.round(hud.height),
      }};
    }}
    // the domain switch, driven for real. The rail's two buttons are the
    // switcher now: CLEAVE opens the void, FUGA opens the shrine.
    const steps = [];
    d.documentElement.dataset.theme = "paper";
    const state = () => steps.push([
      d.documentElement.dataset.theme,
      d.getElementById("domain-btn").getAttribute("aria-pressed"),
      d.getElementById("tech-shrine").getAttribute("aria-pressed"),
    ]);
    state();
    d.getElementById("domain-btn").click(); state();
    d.getElementById("tech-shrine").click(); state();
    d.getElementById("tech-shrine").click(); state();
    d.getElementById("domain-btn").click(); state();
    out.switching = steps;

    // Dismantle has to tear the open domain back down to the base page.
    d.getElementById("tech-shrine").click();
    const opened = d.documentElement.dataset.theme;
    d.getElementById("dismantle-btn").click();
    out.dismantle = [
      opened,
      d.documentElement.dataset.theme,
      d.getElementById("tech-shrine").getAttribute("aria-pressed"),
      d.getElementById("domain-btn").getAttribute("aria-pressed"),
    ];

    /* The pointer must not be able to hide the first box. The two hero planes
       are full-height walls; when they tilted toward the cursor their top edge
       slipped behind the roof that used to hang over them and the box vanished
       under the eaves. The roof is gone now, but the rule stays: hover the
       hero and it must not move and must not take the tilt class. */
    d.documentElement.dataset.theme = "shrine";
    const heroEl = d.querySelector(".panel--hero");
    const before = heroEl.getBoundingClientRect();
    heroEl.dispatchEvent(new d.defaultView.PointerEvent("pointermove", {{
      clientX: before.left + before.width / 2,
      clientY: before.top + 24,
      bubbles: true,
    }}));
    setTimeout(() => {{
      const after = heroEl.getBoundingClientRect();
      out.hover = {{
        tilt: heroEl.classList.contains("tilt"),
        moved: Math.round(Math.abs(after.top - before.top) + Math.abs(after.left - before.left)),
        wBefore: Math.round(before.width),
        wAfter: Math.round(after.width),
      }};
      document.title = "RESULT" + JSON.stringify(out);
    }}, 500);
  }} catch (e) {{ document.title = "ERR(" + e.message + ")"; }}
}}, 4000);
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


def probe(chrome: str, port: int, width: int) -> dict:
    wrapper = SITE / "_verify.html"
    wrapper.write_text(
        WRAPPER.format(w=width, h=1400, port=port, themes=json.dumps(list(THEMES))),
        encoding="utf-8",
    )
    try:
        with tempfile.TemporaryDirectory() as tmp:
            res = subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--no-first-run", "--no-default-browser-check",
                 f"--user-data-dir={tmp}", f"--window-size={max(width + 20, 500)},1400",
                 "--virtual-time-budget=20000", "--dump-dom",
                 f"http://127.0.0.1:{port}/_verify.html"],
                capture_output=True, timeout=220,
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


def serve(port: int) -> socketserver.ThreadingTCPServer:
    """Serve the site on the given port, for as long as the check runs."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a, **k: None
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)
    return httpd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()
    chrome = find_chrome()

    httpd = serve(args.port)
    failures: list[str] = []
    for width in WIDTHS:
        data = probe(chrome, args.port, width)
        print(f"\n== {width}px ==")
        for theme in THEMES:
            info = data[theme]
            overflow = info["scrollW"] - info["clientW"]
            painted = [p for p in info["plates"] if p["display"] != "none"]
            frame_on = bool(info["flameOn"])
            # the two hero boxes must land on the same height, or one of them
            # carries a hole at the bottom
            lopsided = abs(info["heroH"] - info["hudH"])
            ok = overflow <= 0
            # the plates and the neon frame belong to the shrine and nowhere else
            if theme == "shrine":
                ok = ok and len(painted) == 1 and frame_on
            else:
                ok = ok and not painted and not frame_on
            if width >= 1000:
                ok = ok and lopsided <= 4
            flag = "ok " if ok else "FAIL"
            print(
                f"  {flag} {theme:<7} overflow={overflow:>3}px  plates_painted={len(painted)}"
                f"  neon_frame={frame_on}  hero/hud={info['heroH']}/{info['hudH']}"
            )
            if not ok:
                failures.append(
                    f"{width}px {theme}: overflow={overflow} plates={painted}"
                    f" frame={frame_on} lopsided={lopsided}px"
                )

    steps = data.get("switching", [])
    expected = [
        ("paper", "false", "false"),
        ("void", "true", "false"),
        ("shrine", "false", "true"),
        ("shrine", "false", "true"),
        ("void", "true", "false"),
    ]
    print("\n== domain switch ==")
    for i, (got, want) in enumerate(zip(steps, expected)):
        ok = tuple(got) == want
        print(f"  {'ok ' if ok else 'FAIL'} step{i}: theme={got[0]} void={got[1]} shrine={got[2]}")
        if not ok:
            failures.append(f"switch step{i}: got {got} want {want}")

    print("\n== dismantle ==")
    got = data.get("dismantle")
    want = ["shrine", "paper", "false", "false"]
    ok = got == want
    print(f"  {'ok ' if ok else 'FAIL'} opened={got[0] if got else '?'} "
          f"after={got[1] if got else '?'} shrine={got[2] if got else '?'} void={got[3] if got else '?'}")
    if not ok:
        failures.append(f"dismantle: got {got} want {want}")

    print("\n== hover must not hide the first box ==")
    hover = data.get("hover") or {}
    # The static half: the hero planes must stay out of the tilt list. The
    # browser half of the check is skipped when the headless run reports
    # prefers-reduced-motion, so the source is what actually guards it.
    selector = ""
    app_js = SITE / "app.js"
    if app_js.exists():
        src = app_js.read_text(encoding="utf-8")
        m = re.search(r"function wireTilt\(\).*?querySelectorAll\(\s*(.*?)\s*\)", src, re.S)
        selector = " ".join(m.group(1).split()) if m else ""
    listed = ".panel--hero" in selector or ".panel--hud" in selector
    tilt_on = bool(hover.get("tilt"))
    moved = int(hover.get("moved", 999))
    src_ok = not listed
    beh_ok = not tilt_on and moved <= 1
    print(f"  {'ok ' if src_ok else 'FAIL'} tilt list excludes the hero planes: {selector or '(not found)'}")
    print(f"  {'ok ' if beh_ok else 'FAIL'} hero on hover: tilt={tilt_on} moved={moved}px")
    if not src_ok:
        failures.append("the hero panels are back in the tilt list - the roof can hide them again")
    if not beh_ok:
        failures.append(f"hover moved the hero: tilt={tilt_on} moved={moved}px")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        httpd.shutdown()
        return 1
    print("\nAll shrine checks passed.")
    httpd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
