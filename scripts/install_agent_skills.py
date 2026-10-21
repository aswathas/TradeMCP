"""Install Claude Code plugin skills into MiniMax Code's global skill directory.

MiniMax Code loads global skills from ``~/.minimax/skills/<name>/SKILL.md``.
Claude Code plugin skills live under ``~/.claude/plugins/cache/<vendor>/<plugin>/<ver>/skills``.
This copies them across, keeping the plugin's supporting tree (docs, agents) so
relative links inside the skills still resolve.

    python scripts/install_agent_skills.py           # install
    python scripts/install_agent_skills.py --dry-run # preview
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

CLAUDE = Path.home() / ".claude"
TARGET = Path.home() / ".minimax" / "skills"

PLUGINS = [
    {
        "name": "pstack",
        "vendor": "cursor-plugins",
        "version": "0.15.25",
        "carry": ["docs", "agents", "plugin.json", "LICENSE", ".claude-plugin"],
    },
    {
        "name": "ponytail",
        "vendor": "ponytail",
        "version": "5.0.0",
        "carry": ["docs", "plugin.json", "LICENSE"],
    },
]

# Plugin skills reach outside their own folder with ../../docs/... . Once the
# skills sit side by side in ~/.minimax/skills that resolves to ~/.minimax/docs,
# so point it back at the carried plugin tree instead.
REWRITE = [(r"\]\(\.\./\.\./docs/", "](../pstack/docs/")]

# Every skill MiniMax Code already loads names itself with a slug that matches
# its folder. Two pstack skills use title case, which would register them under
# a different label than the folder, so normalise them.
NAME_RE = re.compile(r"^name:\s*.+$", re.M)


def normalise_name(text: str, folder: str) -> str:
    def swap(match: re.Match[str]) -> str:
        return f"name: {folder}"

    return NAME_RE.sub(swap, text, count=1)


def plugin_root(spec: dict) -> Path:
    return CLAUDE / "plugins" / "cache" / spec["vendor"] / spec["name"] / spec["version"]


def rewrite_links(text: str) -> tuple[str, int]:
    hits = 0
    for pattern, replacement in REWRITE:
        text, count = re.subn(pattern, replacement, text)
        hits += count
    return text, hits


def copy_skill(src: Path, dst: Path, dry: bool) -> int:
    if dst.exists():
        shutil.rmtree(dst)
    if dry:
        return 0
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    hits = 0
    for md in dst.rglob("SKILL.md"):
        text = md.read_text(encoding="utf-8")
        text, count = rewrite_links(text)
        hits += count
        text = normalise_name(text, dst.name)
        md.write_text(text, encoding="utf-8")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    TARGET.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    carried: list[str] = []
    rewritten = 0

    for spec in PLUGINS:
        root = plugin_root(spec)
        skills_dir = root / "skills"
        if not skills_dir.is_dir():
            print(f"skip {spec['name']}: not found at {skills_dir}")
            continue

        # Carry the plugin's supporting tree next to the skills.
        for item in spec["carry"]:
            src = root / item
            if not src.exists():
                continue
            dst = TARGET / spec["name"] / item
            if dst.exists() and not args.dry_run:
                shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
            if not args.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
            carried.append(f"{spec['name']}/{item}")

        for skill in sorted(skills_dir.iterdir()):
            if not skill.is_dir():
                continue
            rewritten += copy_skill(skill, TARGET / skill.name, args.dry_run)
            installed.append(f"{spec['name']}/{skill.name}")

    prefix = "would install" if args.dry_run else "installed"
    print(f"{prefix} {len(installed)} skills into {TARGET}")
    print(f"carried {len(carried)} supporting paths")
    print(f"rewrote {rewritten} relative links")
    print()
    for name in installed:
        print("  ", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
