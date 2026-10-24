"""Capture the showcase stills with headless Chrome.

The site is served by scripts/serve_showcase.py on --port. Every shot is a
plain URL, so the same files can be regenerated on any machine with Chrome
installed. No third-party screenshot service, no API key.

Headless Chrome will not paint a scrolled page (only the fixed overlays come
out), so the script captures one tall page per theme and crops the frames it
needs with a second Chrome pass over the PNG.

The one exception is THE CALL frame. It is captured by section name in a real
viewport that is scrolled to the section, because everything above that
section is live and resizes once the data lands: a hard-coded crop offset
drifts by a hundred pixels from run to run.

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

SITE = Path(__file__).resolve().parent.parent / "showcase" / "site"

# theme -> (tall frame height, [(shot name, crop offset), ...])
# The tall frame must be at least offset + FRAME for every crop it feeds.
# The offsets below are measured with scripts/measure_sections.py; re-measure
# them if a section above one of these changes height.
PLAN = {
    "paper": (FRAME, [("01-paper", 0)]),
    "void": (3400, [("02-infinite-void", 0), ("05-live-board-void", 1311)]),
    "shrine": (3800, [("03-malevolent-shrine", 0), ("04-live-board-shrine", 1245)]),
}

# The screener sits directly below the live board, so it moves whenever the
# live board resizes - the same reason THE CALL is framed by name. Captured by
# a fixed offset it drifted by nearly fifty pixels the moment the board's copy
# changed.
SECTIONS = [
    ("06-screener", "screener", 1100, "theme=shrine"),
]

# THE CALL sits below the fold of every other capture, and it is the one frame
# that shows a live handshake rather than a painted result. It is captured by
# name instead of by offset, because everything above it is live: the tape, the
# hero gauge and the metrics chips all resize once the data lands, so a
# hard-coded crop offset drifts by a hundred pixels from run to run. The frame
# is 1170px tall, which fits the sticky masthead, the whole section and a
# little of the next one.
CALL = ("07-call", "call", 1170, "theme=paper")


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


def crop(chrome: str, src: Path, out: Path, offset: int, profile: Path, height: int = FRAME) -> None:
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
    run_chrome(chrome, page.as_uri(), out, height, profile)
    page.unlink(missing_ok=True)


# A section frame, captured by name instead of by offset. The page above a
# section is live, so it resizes once the data lands and a hard-coded crop
# offset drifts. A real viewport that is scrolled to the section cannot drift:
# the frame is the section, wherever the page has put it.
SECTION_WRAPPER = """<!doctype html>
<meta charset="utf-8">
<title>frame</title>
<style>
  html, body {{ margin: 0; padding: 0; background: #000; overflow: hidden; }}
  iframe {{ display: block; border: 0; width: {w}px; height: {h}px; }}
</style>
<iframe src="{url}"></iframe>
<script>
const frame = document.querySelector("iframe");
const seat = () => {{
  try {{
    const d = frame.contentDocument;
    const el = d.getElementById("{anchor}");
    if (!el) return;
    const top = el.getBoundingClientRect().top + d.documentElement.scrollTop;
    /* the masthead is sticky, so the section starts below it, not under it */
    const mast = d.querySelector(".masthead");
    const head = mast ? mast.getBoundingClientRect().height + 12 : 8;
    d.documentElement.scrollTop = top - head;
    frame.contentWindow.scrollTo(0, top - head);
  }} catch (e) {{ /* the page is still loading */ }}
}};
/* Seat it now, and again once the live data has resized the page above. */
[0, 400, 1200, 3000, 6000].forEach((t) => setTimeout(seat, t));
</script>
"""


def capture_section(
    chrome: str, page_url: str, wrapper_url: str, out: Path, anchor: str, height: int, profile: Path
) -> None:
    """Capture one section, framed by its own id.

    The wrapper has to be served from the same origin as the page it frames:
    a wrapper opened from file:// cannot reach into an http:// iframe, so the
    scroll would silently never happen.
    """
    page = SITE / "_section.html"
    page.write_text(
        SECTION_WRAPPER.format(w=WIDTH, h=height, url=page_url, anchor=anchor),
        encoding="utf-8",
    )
    try:
        run_chrome(chrome, wrapper_url, out, height, profile)
    finally:
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
        jobs = [(theme, height, frames, f"theme={theme}") for theme, (height, frames) in PLAN.items()]

        for theme, height, frames, extra in jobs:
            tall = out_dir / f"_tall-{theme}.png"
            url = f"{base}?flat=1&{extra}"
            print(f"capture {tall.name} <- {url}")
            run_chrome(chrome, url, tall, height, profile)
            for frame in frames:
                name, offset = frame[0], frame[1]
                frame_height = frame[2] if len(frame) > 2 else FRAME
                target = out_dir / f"{name}.png"
                print(f"  frame {target.name} at y={offset} h={frame_height}")
                if offset == 0 and height == frame_height:
                    shutil.copyfile(tall, target)
                else:
                    crop(chrome, tall, target, offset, profile, frame_height)
            tall.unlink(missing_ok=True)

        for name, anchor, height, extra in SECTIONS:
            target = out_dir / f"{name}.png"
            page_url = f"{base}?flat=1&{extra}"
            wrapper_url = f"{base}_section.html"
            print(f"capture {target.name} <- {page_url}#{anchor}")
            capture_section(chrome, page_url, wrapper_url, target, anchor, height, profile)

        name, anchor, height, extra = CALL
        target = out_dir / f"{name}.png"
        page_url = f"{base}?flat=1&{extra}"
        wrapper_url = f"{base}_section.html"
        print(f"capture {target.name} <- {page_url}#{anchor}")
        capture_section(chrome, page_url, wrapper_url, target, anchor, height, profile)

    print(f"\nScreenshots written to {out_dir}")


if __name__ == "__main__":
    main()
