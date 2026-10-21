"""Smoke test the server as a real MCP server over stdio.

Launches `python -m trademcp` as a subprocess and talks to it with a genuine
MCP client session, which is how an editor or agent would use it.

    python scripts/smoke_stdio.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


async def main() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "trademcp"],
        env={**os.environ, "PYTHONPATH": os.path.join(ROOT, "src")},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"server: {init.server_info.name} v{init.server_info.version}")

            listing = await session.list_tools()
            print(f"tools advertised over stdio: {len(listing.tools)}")
            for tool in listing.tools:
                print(f"  - {tool.name}")

            result = await session.call_tool("trademcp_get_quote", {"symbol": "RELIANCE"})
            text = result.content[0].text if result.content else ""
            ok = not text.startswith("Error:")
            print()
            print(f"quote call: {'ok' if ok else 'FAILED'}")
            print(text[:400])

            analysis = await session.call_tool(
                "trademcp_get_technical_analysis", {"symbol": "TCS", "range": "6mo"}
            )
            analysis_text = analysis.content[0].text if analysis.content else ""
            print()
            print("technical analysis excerpt:")
            print(analysis_text[:600])

            return 0 if ok and not analysis_text.startswith("Error:") else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
