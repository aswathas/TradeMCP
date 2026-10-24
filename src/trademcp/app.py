"""The MCPServer instance.

Tools live in :mod:`trademcp.tools` and register themselves onto this object.
"""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    name="trademcp",
    title="TradeMCP - Indian Markets",
    version="0.1.0",
    instructions=(
        "Indian equity market intelligence (NSE/BSE): live quotes, OHLCV history, 57 technical "
        "indicators, fundamental ratios, financial statements, stock screeners and portfolio "
        "analytics. Backed entirely by free public data sources - no API keys required."
    ),
)
