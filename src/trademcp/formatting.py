"""Rendering helpers: one generic markdown/JSON renderer for every tool."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def humanize(key: str) -> str:
    """'price_to_book' -> 'Price To Book'."""
    return key.replace("_", " ").strip().title()


class Raw(float):
    """A number that should be printed exactly as given, without lakh/crore scaling."""


def fmt_number(value: Any) -> str:
    """Format a value for humans, using Indian crore/lakh units for big numbers."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, Raw):
        return f"{float(value):,.2f}"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value != value:  # NaN
            return "-"
        if abs(value) >= 1e7:
            return f"{value / 1e7:,.2f} Cr"
        if abs(value) >= 1e5:
            return f"{value / 1e5:,.2f} L"
        if isinstance(value, int):
            return f"{value:,}"
        return f"{value:,.2f}"
    return str(value)


def fmt_epoch(value: Any) -> str | None:
    """Unix epoch seconds -> a readable timestamp (else None)."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError, OSError):
        return None


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["_no data_"]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    out = ["| " + " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)) + " |"]
    out.append("|" + "|".join("-" * (w + 2) for w in widths) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)) + " |")
    return out


def _render(value: Any) -> list[str]:
    if isinstance(value, dict):
        if not value:
            return ["_no data_"]
        if all(not isinstance(v, (dict, list)) for v in value.values()):
            return _table(
                ["Metric", "Value"],
                [[humanize(k), fmt_number(v)] for k, v in value.items()],
            )
        out: list[str] = []
        for key, sub in value.items():
            out.append(f"### {humanize(key)}")
            out.append("")
            out.extend(_render(sub))
            out.append("")
        return out
    if isinstance(value, list):
        if not value:
            return ["_no data_"]
        if all(isinstance(v, dict) for v in value):
            headers: list[str] = []
            for item in value:
                for key in item:
                    if key not in headers:
                        headers.append(key)
            rows = [[fmt_number(item.get(h)) for h in headers] for item in value]
            return _table([humanize(h) for h in headers], rows)
        return [f"- {fmt_number(v)}" for v in value]
    return [fmt_number(value)]


def to_markdown(payload: dict[str, Any], title: str | None = None) -> str:
    """Render a nested payload as readable markdown."""
    lines: list[str] = []
    if title:
        lines += [f"# {title}", ""]
    for key, value in payload.items():
        lines.append(f"## {humanize(key)}")
        lines.append("")
        lines.extend(_render(value))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, default=str)
