"""Experiment: connect to our MCP server as a client and see what it offers."""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Always find server.py next to this file, wherever the program is started from
SERVER_PATH = Path(__file__).parent / "server.py"
server = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])


async def main():
    # 1. Start server.py and open a connection to it (over stdin/stdout)
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            # 2. The MCP "handshake": client and server introduce themselves
            await session.initialize()

            # 3. Ask the server what tools it has
            result = await session.list_tools()
            for tool in result.tools:
                print("TOOL:", tool.name)
                print("  description:", tool.description)
                print("  inputs:", tool.input_schema)
                print()

            # 4. Ask the server to run one tool
            answer = await session.call_tool("find_place", {"name": "Hobart"})
            print("find_place result:", answer.content[0].text)


asyncio.run(main())