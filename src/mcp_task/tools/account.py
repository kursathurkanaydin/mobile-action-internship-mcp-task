from mcp_task.ma_client import MobileActionAPIError, get
from mcp_task.mcp_instance import mcp


@mcp.tool
def get_remaining_api_credits() -> dict:
    """Check the MobileAction API key's credit balance (total, remaining, reset period).

    Use this before running several tool calls in a row, or whenever the user
    asks how many credits/tokens are left on the API key.
    """
    try:
        data = get("/api-key")
    except MobileActionAPIError as exc:
        return {"error": exc.message, "status_code": exc.status_code}

    return data
