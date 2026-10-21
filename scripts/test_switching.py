"""Click the page's own buttons and report what actually changed.

A theme switch that looks broken on a phone is usually a layering problem
or an exception in the click handler, not a styling problem. This drives the
real page in headless Chrome: it clicks the theme toggle and each domain
button, then reads back documentElement.dataset.theme, the aria-pressed
states and the computed z-index of the overlay layers.

    python scripts/test_switching.py --port 8099
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

PROBE = """<!doctype html>
<meta charset="utf-8">
<title>probe</title>
<script>
const params = new URLSearchParams(location.search);
fetch("/index.html")
  .then((r) => r.text())
  .then((html) => {
    document.open(); document.write(html); document.close();
    setTimeout(() => {
      const out = { steps: [], errors: [] };
      window.addEventListener("error", (e) => out.errors.push(String(e.message)));
      const state = (label) => {
        const theme = document.documentElement.dataset.theme;
        const pressed = Array.from(document.querySelectorAll("[aria-pressed]"))
          .map((b) => (b.id || b.className) + "=" + b.getAttribute("aria-pressed"));
        out.steps.push({
          label,
          theme,
          pressed: pressed.join(" "),
          domainZ: getComputedStyle(document.getElementById("domain")).zIndex,
          sheetZ: getComputedStyle(document.querySelector(".sheet")).zIndex,
          mastheadZ: getComputedStyle(document.querySelector(".masthead")).zIndex,
          cutPointer: getComputedStyle(document.getElementById("cut")).pointerEvents,
        });
      };
      const click = (id) => {
        const b = document.getElementById(id);
        if (!b) { out.errors.push("missing #" + id); return; }
        b.click();
      };
      state("load");
      click("theme-toggle");
      state("after theme-toggle");
      click("theme-toggle");
      state("after theme-toggle x2");
      click("domain-void");
      state("after domain-void");
      click("domain-shrine");
      state("after domain-shrine");
      click("domain-shrine");
      state("after domain-shrine again");
      click("theme-toggle");
      state("after theme-toggle from void");
      document.title = "RESULT" + JSON.stringify(out);
    }, 2600);
  });
</script>
"""


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("google-chrome") or shutil.which("chromium")
    if found:
        return found
    raise SystemExit("No Chrome found.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()

    chrome = find_chrome()
    probe = SITE / "_probe.html"
    probe.write_text(PROBE, encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [
                chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--no-first-run", "--no-default-browser-check",
                f"--user-data-dir={tmp}", "--window-size=1440,1000",
                "--virtual-time-budget=15000", "--dump-dom",
                f"http://127.0.0.1:{args.port}/_probe.html",
            ],
            capture_output=True, timeout=200,
        )
    stdout = result.stdout.decode("utf-8", "replace")

    match = re.search(r"RESULT(\{.*?\})</title>", stdout, re.S)
    if not match:
        print("no result")
        print(stdout[-700:])
        return 1
    data = json.loads(match.group(1))
    for step in data["steps"]:
        print(f"{step['label']:<28} theme={step['theme']:<7} z(domain)={step['domainZ']:<4} "
              f"z(sheet)={step['sheetZ']:<4} z(masthead)={step['mastheadZ']}")
        print(f"{'':<28} {step['pressed']}")
    if data["errors"]:
        print("ERRORS:", data["errors"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
