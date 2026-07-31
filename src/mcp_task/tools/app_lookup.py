import httpx
import pycountry

from mcp_task.mcp_instance import mcp


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
        response = httpx.get(
            "https://itunes.apple.com/search",
            params={"term": app_name, "entity": "software", "country": country, "limit": 1},
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {"error": f"Failed to search the App Store: {exc}"}

    results = response.json().get("results", [])
    if not results:
        return {"error": f"No app found for '{app_name}' in storefront '{country}'"}

    app = results[0]
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
        response = httpx.get(
            "https://itunes.apple.com/lookup",
            params={"id": track_id, "country": country},
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {"error": f"Failed to look up the App Store id: {exc}"}

    results = response.json().get("results", [])
    if not results:
        return {"error": f"No app found for trackId {track_id} in storefront '{country}'"}

    app = results[0]
    return {
        "app_id": app["trackId"],
        "name": app["trackName"],
        "url": app["trackViewUrl"],
    }


# pycountry's ISO dataset uses each country's current official/UN-registered name
# (e.g. Turkey is listed as "Türkiye"), which breaks lookups for common
# English names that changed. Resolve well-known mismatches before falling
# back to fuzzy search.
_COUNTRY_NAME_ALIASES = {
    "turkey": "TR",
}