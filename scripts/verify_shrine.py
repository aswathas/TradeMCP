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
      const plates = Array.from(d.querySelectorAll(".shrine-roof, .shrine-fangs"))
        .map((el) => {{
          const cs = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return {{ display: cs.display, w: Math.round(r.width), h: Math.round(r.height) }};
        }});
      const frame = getComputedStyle(d.querySelector(".panel--hero"), "::after");
      out[theme] = {{
        scrollW: d.documentElement.scrollWidth,
        clientW: d.documentElement.clientWidth,
        plates: plates,
        frameImage: frame.borderImageSource,
      }};
    }}
    // the domain switch, driven for real
    const steps = [];
    d.documentElement.dataset.theme = "paper";
    const state = () => steps.push([
      d.documentElement.dataset.theme,
      d.getElementById("domain-void").getAttribute("aria-pressed"),
      d.getElementById("domain-shrine").getAttribute("aria-pressed"),
    ]);
    state();
    d.getElementById("domain-void").click(); state();
    d.getElementById("domain-shrine").click(); state();
    d.getElementById("domain-shrine").click(); state();
    d.getElementById("domain-void").click(); state();
    out.switching = steps;
    document.title = "RESULT" + JSON.stringify(out);
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()
    chrome = find_chrome()

    failures: list[str] = []
    for width in WIDTHS:
        data = probe(chrome, args.port, width)
        print(f"\n== {width}px ==")
        for theme in THEMES:
            info = data[theme]
            overflow = info["scrollW"] - info["clientW"]
            painted = [p for p in info["plates"] if p["display"] != "none"]
            frame_on = "none" not in (info["frameImage"] or "none")
            ok = overflow <= 0
            # the plates and the neon frame belong to the shrine and nowhere else
            if theme == "shrine":
                ok = ok and len(painted) == 2 and frame_on
            else:
                ok = ok and not painted and not frame_on
            flag = "ok " if ok else "FAIL"
            print(f"  {flag} {theme:<7} overflow={overflow:>3}px  plates_painted={len(painted)}  neon_frame={frame_on}")
            if not ok:
                failures.append(f"{width}px {theme}: overflow={overflow} plates={painted} frame={frame_on}")

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

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nAll shrine checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
