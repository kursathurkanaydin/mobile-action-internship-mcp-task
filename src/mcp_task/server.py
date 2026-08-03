import asyncio
import sys

from mcp_task.mcp_instance import mcp


async def main() -> None:
    tools = await mcp.list_tools()

    # stdout is the MCP JSON-RPC channel once mcp.run_async() starts (stdio
    # transport), so this startup log must go to stderr instead — anything
    # printed to stdout here would corrupt the protocol stream for the client.
    print(f"MobileAction MCP Server - {len(tools)} tool(s) registered:", file=sys.stderr)
    for tool in tools:
        summary = (tool.description or "").strip().splitlines()[0] if tool.description else "(no description)"
        print(f"  - {tool.name}: {summary}", file=sys.stderr)

    await mcp.run_async()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()