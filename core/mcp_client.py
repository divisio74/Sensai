import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@asynccontextmanager
async def _session():
    # the SDK only forwards a few safe variables by default: pass them all so the
    # server gets LANGSEARCH_API_KEY
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).parent / "mcp_server.py")],
        env=dict(os.environ)
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def _list_tools():
    async with _session() as session:
        return (await session.list_tools()).tools


async def _call_tool(name, arguments):
    async with _session() as session:
        return await session.call_tool(name, arguments)


def get_tools():
    """Tools of the MCP server, in the format expected by Ollama's `tools` field."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in asyncio.run(_list_tools())
    ]


def call_tool(name, arguments):
    result = asyncio.run(_call_tool(name, arguments))
    text = "\n".join(block.text for block in result.content if block.type == "text")
    if result.isError:
        raise RuntimeError(text or f"Tool '{name}' failed")
    return text
