"""Entry point: ``python -m trademcp`` starts the MCP server on stdio."""

from __future__ import annotations

import logging
import sys

from . import tools  # noqa: F401  (importing registers the tools)
from .app import mcp


def main() -> None:
    """Run the MCP server. Logs go to stderr so stdout stays clean for the protocol."""
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
