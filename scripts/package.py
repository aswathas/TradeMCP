"""Package the TradeMCP source into a shareable zip (no venv, caches or build artefacts)."""

from __future__ import annotations

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(ROOT), "TradeMCP-v0.1.0.zip")

SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git"}
SKIP_SUFFIX = (".pyc", ".pyo", ".zip")
SKIP_NAMES = {".DS_Store"}


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.endswith(".egg-info")


def main() -> None:
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
            for name in filenames:
                if name in SKIP_NAMES or name.endswith(SKIP_SUFFIX):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
                archive.write(full, f"TradeMCP/{rel}")
                count += 1

    size_kb = os.path.getsize(OUT) / 1024
    print(f"wrote {OUT} ({count} files, {size_kb:.1f} KB)")
    with zipfile.ZipFile(OUT) as archive:
        for entry in sorted(archive.namelist()):
            print("  ", entry)


if __name__ == "__main__":
    main()
