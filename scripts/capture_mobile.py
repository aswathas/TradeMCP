"""Capture the showcase the way a phone actually renders it.

Chrome enforces a minimum window width of 500px, so --window-size=390 does
NOT give a 390px viewport: the page renders at 500px and the screenshot is
cropped to 390. Every "mobile" screenshot taken that way is a lie — the right
edge is cut, not overflowed.

The fix is an iframe of the exact target width. The inner document then has
the real viewport (media queries fire at the right width) and the outer
window stays at 500px. The PNG is cropped back to the iframe width.

    python scripts/capture_mobile.py --port 8099 --width 390 --height 1500
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

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
<style>
  html, body {{ margin: 0; padding: 0; background: #000; overflow: hidden; }}
  iframe {{ display: block; border: 0; width: {w}px; height: {h}px; }}
</style>
<iframe src="{url}"></iframe>
"""


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("google-chrome") or shutil.which("chromium")
    if found:
        return found
    raise SystemExit("No Chrome found.")


def capture(chrome: str, port: int, width: int, height: int, theme: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out = out.resolve()
    wrapper = SITE / "_frame.html"
    url = f"http://127.0.0.1:{port}/index.html?theme={theme}"
    wrapper.write_text(WRAPPER.format(w=width, h=height, url=url), encoding="utf-8")

    # the window must be at least 500 wide; the iframe does the narrowing
    window_w = max(width + 20, 500)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [
                chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--no-first-run", "--no-default-browser-check",
                f"--user-data-dir={tmp}", f"--window-size={window_w},{height}",
                "--virtual-time-budget=16000",
                f"--screenshot={out}",
                f"http://127.0.0.1:{port}/_frame.html",
            ],
            capture_output=True, timeout=200,
        )
    if not out.exists():
        raise SystemExit(f"no screenshot for theme={theme}")

    # crop back to the iframe's width
    with Image.open(out) as im:
        if im.width != width:
            im.crop((0, 0, min(width, im.width), im.height)).save(out)
    wrapper.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--width", type=int, default=390)
    parser.add_argument("--height", type=int, default=1500)
    parser.add_argument("--themes", default="paper,void,shrine")
    parser.add_argument("--out", default="logs/mobile")
    args = parser.parse_args()

    chrome = find_chrome()
    out_dir = Path(args.out)
    for theme in [t.strip() for t in args.themes.split(",") if t.strip()]:
        target = out_dir / f"mobile-{args.width}-{theme}.png"
        capture(chrome, args.port, args.width, args.height, theme, target)
        with Image.open(target) as im:
            print(f"{theme}: {target} {im.width}x{im.height}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
