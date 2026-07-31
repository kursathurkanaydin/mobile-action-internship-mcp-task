from fastmcp import FastMCP

mcp = FastMCP("MobileAction MCP Server")

from mcp_task.tools import account, app_lookup, keyword_services  # noqa: E402, F401  (registers tools)
