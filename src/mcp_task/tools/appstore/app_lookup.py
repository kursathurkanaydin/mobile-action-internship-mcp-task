from mcp_task.errors import handle_tool_errors, with_credit_usage
from mcp_task.mcp_instance import mcp
from mcp_task.services.appstore.app_service import fetch_app_by_name, fetch_app_by_track_id, fetch_apps_by_track_ids


@mcp.tool
@with_credit_usage
@handle_tool_errors
def get_app_store_id(app_name: str, country: str = "us") -> dict:
    """Look up an app's numeric App Store id (trackId) by its name.

    MobileAction's endpoints require a numeric trackId rather than an app name,
    so call this first when the user refers to an app by name (e.g. "Clash of
    Clans") to resolve it to the id needed by other tools.

    Args:
        app_name: The app's name as it appears on the App Store.
        country: Two-letter App Store storefront code to search in, e.g. "us", "tr".
    """
    app = fetch_app_by_name(app_name, country)
    return {
        "app_id": app["trackId"],
        "name": app["trackName"],
        "url": app["trackViewUrl"],
    }


@mcp.tool
@with_credit_usage
@handle_tool_errors
def get_app_name(track_id: int, country: str = "us") -> dict:
    """Look up an app's name and details by its numeric App Store id (trackId).

    This is the reverse of get_app_id: use it when the user gives a trackId
    (e.g. from a MobileAction tool result) and asks what app it is.

    Do NOT call this once per id in a loop when you have TWO OR MORE trackIds
    to resolve at once (e.g. the competitor list from get_apps_for_keyword) —
    use get_app_names_batch instead; it resolves all of them in a single
    request.

    Args:
        track_id: The app's numeric App Store id, e.g. 570060128.
        country: Two-letter App Store storefront to look the app up in, e.g. "us", "tr".
    """
    app = fetch_app_by_track_id(track_id, country)
    return {
        "app_id": app["trackId"],
        "name": app["trackName"],
        "url": app["trackViewUrl"],
    }


@mcp.tool
@with_credit_usage
@handle_tool_errors
def get_app_names_batch(track_ids: str, country: str = "us") -> dict:
    """Look up names/details for MULTIPLE numeric App Store ids (trackIds) in one request.

    This is the tool to call whenever you already have two or more numeric
    trackIds to resolve to names — most commonly the competitor list returned
    by get_apps_for_keyword. Call this ONCE with all of them comma-separated;
    do not call get_app_name once per id in a loop, since iTunes' lookup
    endpoint accepts a comma-joined id list directly and resolves all of them
    in a single HTTP request instead of N.

    Ids iTunes doesn't recognize are reported separately in "not_found_ids"
    rather than causing the whole call to fail.

    Args:
        track_ids: One or more numeric App Store ids, comma-separated
            (e.g. "570060128,389801252,284882215"). Up to BATCH_LOOKUP_MAX_IDS
            (default 300, configurable via env var) per call.
        country: Two-letter App Store storefront to look the apps up in, e.g. "us", "tr".
    """
    requested_ids, apps = fetch_apps_by_track_ids(track_ids, country)
    found_ids = {app["trackId"] for app in apps}

    return {
        "apps": [
            {"app_id": app["trackId"], "name": app["trackName"], "url": app["trackViewUrl"]} for app in apps
        ],
        "not_found_ids": [track_id for track_id in requested_ids if track_id not in found_ids],
    }
