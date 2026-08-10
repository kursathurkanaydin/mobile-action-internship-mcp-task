import importlib
import pkgutil

from fastmcp import FastMCP

mcp = FastMCP("MobileAction MCP Server")

# Every module under mcp_task.tools (including subpackages like
# tools/appstore/, tools/playstore/) is expected to register its tools via
# @mcp.tool at import time, so just importing each one is enough — new tool
# files or store subpackages don't need to be wired in here by hand.
# walk_packages (not iter_modules) is required here specifically because it
# recurses into subpackages; iter_modules only sees top-level tools/*.py.
from mcp_task import tools  # noqa: E402

for _module_info in pkgutil.walk_packages(tools.__path__, prefix=f"{tools.__name__}."):
    importlib.import_module(_module_info.name)
