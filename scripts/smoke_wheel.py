"""Start the built wheel in an isolated uvx environment and check it answers MCP over stdio.

Usage: uv run python scripts/smoke_wheel.py dist/mcp_variety-0.1.0-py3-none-any.whl
"""

import asyncio
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {"variety_pick", "variety_kinds", "variety_check"}
START_TIMEOUT_SECONDS = 180


async def smoke(wheel: str) -> None:
    with tempfile.TemporaryDirectory() as state_dir:
        params = StdioServerParameters(
            command="uvx",
            args=["--from", wheel, "mcp-variety"],
            env={"VARIETY_MCP_STATE_DIR": state_dir},
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            init = await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            if tools != EXPECTED_TOOLS:
                raise SystemExit(f"smoke test failed: tools were {sorted(tools)}")
            print(f"ok: {init.serverInfo.name} answered initialize and tools/list with {sorted(tools)}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    asyncio.run(asyncio.wait_for(smoke(sys.argv[1]), START_TIMEOUT_SECONDS))


if __name__ == "__main__":
    main()
