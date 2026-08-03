import httpx

from mcp_task.errors import ToolError

_TIMEOUT = 15


class AppLookupError(ToolError):
    """A clean, user-facing error for an iTunes lookup that failed or found nothing."""


def search_app(app_name: str, country: str) -> dict:
    """Search the App Store by name and return the first matching app."""
    try:
        response = httpx.get(
            "https://itunes.apple.com/search",
            params={"term": app_name, "entity": "software", "country": country, "limit": 1},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AppLookupError(f"Failed to search the App Store: {exc}") from exc

    results = response.json().get("results", [])
    if not results:
        raise AppLookupError(f"No app found for '{app_name}' in storefront '{country}'")

    return results[0]


def lookup_app(track_id: int, country: str) -> dict:
    """Look up an app on the App Store by its numeric trackId."""
    try:
        response = httpx.get(
            "https://itunes.apple.com/lookup",
            params={"id": track_id, "country": country},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AppLookupError(f"Failed to look up the App Store id: {exc}") from exc

    results = response.json().get("results", [])
    if not results:
        raise AppLookupError(f"No app found for trackId {track_id} in storefront '{country}'")

    return results[0]
