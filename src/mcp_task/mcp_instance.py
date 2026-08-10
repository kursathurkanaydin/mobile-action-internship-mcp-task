import importlib
import pkgutil

from fastmcp import FastMCP

mcp = FastMCP("MobileAction MCP Server")

# Every module under mcp_task.tools is expected to register its tools via
# @mcp.tool at import time, so just importing each one is enough — new tool
# files don't need to be wired in here by hand.
from mcp_task import tools  # noqa: E402

for _module_info in pkgutil.iter_modules(tools.__path__, prefix=f"{tools.__name__}."):
    importlib.import_module(_module_info.name)
