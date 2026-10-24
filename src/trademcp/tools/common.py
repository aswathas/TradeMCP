"""Shared bits for the tool modules: response formats, rendering, error text."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from ..formatting import to_json, to_markdown

if TYPE_CHECKING:
    from mcp.types import ToolAnnotations


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


def render(payload: dict[str, Any], response_format: ResponseFormat, title: str) -> str:
    """Return the payload as markdown or JSON, per the caller's choice."""
    if response_format == ResponseFormat.JSON:
        return to_json(payload)
    return to_markdown(payload, title)


def error_text(exc: Exception) -> str:
    """A short, actionable error string for the LLM to relay."""
    message = str(exc)
    return f"Error: {message}"


def tool_annotations(title: str) -> "ToolAnnotations":
    """Annotations for read-only market data tools."""
    from mcp.types import ToolAnnotations

    return ToolAnnotations(
        title=title,
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
