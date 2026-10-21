"""Measure how long a real MCP client waits for the server to say hello.

    python scripts/measure_startup.py [--cold]

Cold means the launcher's virtualenv cache is removed first, so this is the
worst case a first-time user hits.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCHER = os.path.join(ROOT, "bin", "trademcp.js")
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "trademcp-npm")


async def main() -> int:
    if "--cold" in sys.argv and os.path.isdir(CACHE):
        shutil.rmtree(CACHE, ignore_errors=True)
        print("cache wiped - cold run")

    params = StdioServerParameters(command="node", args=[LAUNCHER], env={**os.environ})

    started = time.monotonic()
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            handshake = time.monotonic() - started
            listing = await session.list_tools()
            listed = time.monotonic() - started
            result = await session.call_tool("trademcp_get_quote", {"symbol": "TCS"})
            quoted = time.monotonic() - started

    print(f"handshake      {handshake:6.1f}s  ({init.server_info.name} {init.server_info.version})")
    print(f"tools listed   {listed:6.1f}s  ({len(listing.tools)} tools)")
    print(f"live quote     {quoted:6.1f}s  ({'ok' if result.content else 'no content'})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
