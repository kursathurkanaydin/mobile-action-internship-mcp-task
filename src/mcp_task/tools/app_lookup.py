from mcp_task.errors import ToolError, to_error_response
from mcp_task.mcp_instance import mcp
from mcp_task.services.app_service import fetch_app_by_name, fetch_app_by_track_id


@mcp.tool
def get_app_store_id(app_name: str, country: str = "us") -> dict:
    """Look up an app's numeric App Store id (trackId) by its name.

    MobileAction's endpoints require a numeric trackId rather than an app name,
    so call this first when the user refers to an app by name (e.g. "Clash of
    Clans") to resolve it to the id needed by other tools.

    Args:
        app_name: The app's name as it appears on the App Store.
        country: Two-letter App Store storefront code to search in, e.g. "us", "tr".
    """
    try:
        app = fetch_app_by_name(app_name, country)
    except ToolError as exc:
        return to_error_response(exc)

    return {
        "app_id": app["trackId"],
        "name": app["trackName"],
        "url": app["trackViewUrl"],
    }


@mcp.tool
def get_app_name(track_id: int, country: str = "us") -> dict:
    """Look up an app's name and details by its numeric App Store id (trackId).

    This is the reverse of get_app_id: use it when the user gives a trackId
    (e.g. from a MobileAction tool result) and asks what app it is.

    Args:
        track_id: The app's numeric App Store id, e.g. 570060128.
        country: Two-letter App Store storefront to look the app up in, e.g. "us", "tr".
    """
    try:
        app = fetch_app_by_track_id(track_id, country)
    except ToolError as exc:
        return to_error_response(exc)

    return {
        "app_id": app["trackId"],
        "name": app["trackName"],
        "url": app["trackViewUrl"],
    }
