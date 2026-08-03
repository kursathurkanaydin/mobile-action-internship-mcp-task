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


def lookup_apps(track_ids: list[int], country: str) -> list[dict]:
    """Look up several apps in one request by passing comma-joined trackIds.

    iTunes' lookup endpoint accepts a comma-separated id list directly, so N
    apps cost one HTTP round trip instead of N. Ids iTunes doesn't recognize
    are simply absent from the returned list — no per-id error is raised
    here, since that's expected for a batch call; the caller can diff the
    requested ids against the returned trackIds to see what's missing.
    """
    ids_param = ",".join(str(track_id) for track_id in track_ids)
    try:
        response = httpx.get(
            "https://itunes.apple.com/lookup",
            params={"id": ids_param, "country": country},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AppLookupError(f"Failed to look up App Store ids: {exc}") from exc

    return response.json().get("results", [])
