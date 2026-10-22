"""Capture the showcase stills with headless Chrome.

The site is served by scripts/serve_showcase.py on --port. Every shot is a
plain URL, so the same files can be regenerated on any machine with Chrome
installed. No third-party screenshot service, no API key.

Headless Chrome will not paint a scrolled page (only the fixed overlays come
out), so the script captures one tall page per theme and crops the frames it
needs with a second Chrome pass over the PNG.

    python scripts/capture_screenshots.py --port 8099 --out showcase/screenshots
"""

from __future__ import annotations

import argparse
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

WIDTH = 1440
FRAME = 900

# theme -> (tall frame height, [(shot name, crop offset), ...])
# The tall frame must be at least offset + FRAME for every crop it feeds.
PLAN = {
    "paper": (FRAME, [("01-paper", 0)]),
    "void": (3400, [("02-infinite-void", 0), ("05-live-board-void", 1150)]),
    "shrine": (3800, [("03-malevolent-shrine", 0), ("04-live-board-shrine", 1560), ("06-screener", 2650)]),
}


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("google-chrome") or shutil.which("chromium")
    if found:
        return found
    raise SystemExit("No Chrome or Chromium found. Install Chrome or pass --chrome.")


def run_chrome(chrome: str, url: str, out: Path, height: int, profile: Path) -> None:
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={profile}",
        f"--window-size={WIDTH},{height}",
        "--virtual-time-budget=22000",
        f"--screenshot={out}",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not out.exists():
        sys.stderr.write(result.stderr[-2000:])
        raise SystemExit(f"Chrome produced no screenshot for {url}")


def crop(chrome: str, src: Path, out: Path, offset: int, profile: Path) -> None:
    """Cut a frame out of a tall capture by rendering the PNG in a wrapper."""
    page = src.with_suffix(".frame.html")
    page.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<style>html,body{margin:0;background:#000;overflow:hidden}"
        f"img{{position:absolute;left:0;top:-{offset}px;width:{WIDTH}px;height:auto;display:block}}"
        "</style>"
        f"<img src='file:///{src.as_posix()}'>",
        encoding="utf-8",
    )
    run_chrome(chrome, page.as_uri(), out, FRAME, profile)
    page.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--out", default="showcase/screenshots")
    parser.add_argument("--chrome", default=None)
    args = parser.parse_args()

    chrome = args.chrome or find_chrome()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"http://localhost:{args.port}/"

    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "chrome-profile"
        for theme, (height, frames) in PLAN.items():
            tall = out_dir / f"_tall-{theme}.png"
            url = f"{base}?flat=1&theme={theme}"
            print(f"capture {tall.name} <- {url}")
            run_chrome(chrome, url, tall, height, profile)
            for name, offset in frames:
                target = out_dir / f"{name}.png"
                print(f"  frame {target.name} at y={offset}")
                if offset == 0 and height == FRAME:
                    shutil.copyfile(tall, target)
                else:
                    crop(chrome, tall, target, offset, profile)
            tall.unlink(missing_ok=True)
    print(f"\nScreenshots written to {out_dir}")


if __name__ == "__main__":
    main()
