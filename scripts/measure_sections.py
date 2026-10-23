"""One-off: measure where each section sits at a given width.

    python scripts/measure_sections.py --port 8099 --width 1440
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

WRAPPER = """<!doctype html>
<meta charset="utf-8">
<title>probe</title>
<style>html,body{{margin:0;padding:0;overflow:hidden}}iframe{{display:block;border:0;width:{w}px;height:1200px}}</style>
<iframe src="http://127.0.0.1:{port}/index.html?flat=1&theme={theme}"></iframe>
<script>
setTimeout(() => {{
  try {{
    const d = document.querySelector("iframe").contentDocument;
    const out = {{}};
    for (const id of {ids}) {{
      const el = d.getElementById(id);
      if (!el) {{ out[id] = null; continue; }}
      const r = el.getBoundingClientRect();
      out[id] = {{ top: Math.round(r.top + d.documentElement.scrollTop),
                  height: Math.round(r.height) }};
    }}
    out.pageHeight = d.documentElement.scrollHeight;
    document.title = "RESULT" + JSON.stringify(out);
  }} catch (e) {{ document.title = "ERR(" + e.message + ")"; }}
}}, 6000);
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--theme", default="paper")
    ap.add_argument("--ids", default="call,how,metrics,sources,install,live,screener,tools")
    args = ap.parse_args()

    chrome = find_chrome()
    ids = [i.strip() for i in args.ids.split(",") if i.strip()]
    wrapper = SITE / "_measure.html"
    wrapper.write_text(
        WRAPPER.format(w=args.width, port=args.port, theme=args.theme, ids=json.dumps(ids)),
        encoding="utf-8",
    )
    try:
        with tempfile.TemporaryDirectory() as tmp:
            res = subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--no-first-run", "--no-default-browser-check",
                 f"--user-data-dir={tmp}", f"--window-size={max(args.width + 20, 500)},1200",
                 "--virtual-time-budget=30000", "--dump-dom",
                 f"http://127.0.0.1:{args.port}/_measure.html"],
                capture_output=True, timeout=260,
            )
    finally:
        wrapper.unlink(missing_ok=True)

    out = res.stdout.decode("utf-8", "replace")
    m = re.search(r"<title>(RESULT|ERR)(.*?)</title>", out, re.S)
    if not m:
        raise SystemExit(f"no result:\n{out[-800:]}")
    if m.group(1) == "ERR":
        raise SystemExit(f"probe error: {m.group(2)}")
    data = json.loads(m.group(2))
    for k, v in data.items():
        if isinstance(v, dict):
            print(f"{k:<10} top={v['top']:>6}  height={v['height']:>5}")
        else:
            print(f"{k:<10} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
