import asyncio

from mcp_task.mcp_instance import mcp


async def main() -> None:
    tools = await mcp.list_tools()

    print(f"MobileAction MCP Server - {len(tools)} tool(s) registered:")
    for tool in tools:
        summary = (tool.description or "").strip().splitlines()[0] if tool.description else "(no description)"
        print(f"  - {tool.name}: {summary}")

    await mcp.run_async()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()