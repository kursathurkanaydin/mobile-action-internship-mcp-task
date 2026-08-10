from mcp_task.clients.mobileaction import get
from mcp_task.errors import handle_tool_errors
from mcp_task.mcp_instance import mcp


@mcp.tool
@handle_tool_errors
def get_remaining_api_credits() -> dict:
    """Check the MobileAction API key's credit balance (total, remaining, reset period).

    Use this before running several tool calls in a row, or whenever the user
    asks how many credits/tokens are left on the API key.
    """
    return get("/api-key")
