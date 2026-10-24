"""Smoke test the npm launcher as a real MCP server over stdio.

Launches `node bin/trademcp.js` the way an MCP client would and talks to it
with a genuine client session.

    python scripts/smoke_npx.py          # session only, no network
    python scripts/smoke_npx.py --call   # also call a tool (needs the network)

The asserted part is the session shape - initialize plus a non-empty tool
list - and that needs no network. The tool call is OPTIONAL because it hits
the live quote provider, so it only runs with --call.
"""

from __future__ import annotations

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCHER = os.path.join(ROOT, "bin", "trademcp.js")


async def main(call_tool: bool) -> int:
    params = StdioServerParameters(
        command="node",
        args=[LAUNCHER],
        env={**os.environ},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"server: {init.server_info.name} v{init.server_info.version}")

            listing = await session.list_tools()
            names = [tool.name for tool in listing.tools]
            print(f"tools over stdio through node: {len(names)}")
            if not names:
                print("FAILED: the server listed no tools")
                return 1
            if "trademcp_get_quote" not in names:
                print("FAILED: trademcp_get_quote is missing from the tool list")
                return 1

            # Optional: the tool call needs the network, the session above does not.
            if not call_tool:
                print("tool call skipped (it needs the network) - run with --call to include it")
                return 0

            result = await session.call_tool("trademcp_get_quote", {"symbol": "RELIANCE"})
            text = result.content[0].text if result.content else ""
            ok = not text.startswith("Error:")
            print(f"quote call: {'ok' if ok else 'FAILED'}")
            print(text[:300])
            return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(call_tool="--call" in sys.argv[1:])))
