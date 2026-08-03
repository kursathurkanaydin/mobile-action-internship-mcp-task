from mcp_task.clients.mobileaction import get
from mcp_task.errors import ToolInputError, to_error_response
from mcp_task.mcp_instance import mcp


@mcp.tool
def get_remaining_api_credits() -> dict:
    """Check the MobileAction API key's credit balance (total, remaining, reset period).

    Use this before running several tool calls in a row, or whenever the user
    asks how many credits/tokens are left on the API key.
    """
    try:
        data = get("/api-key")
    except ToolInputError as exc:
        return to_error_response(exc)

    return data
