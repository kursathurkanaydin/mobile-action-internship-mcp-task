from mcp_task.errors import ToolError, to_error_response
from mcp_task.mcp_instance import mcp
from mcp_task.services.playstore.app_service import fetch_app_by_track_id, fetch_apps_by_track_ids


def _app_url(track_id: str) -> str:
    return f"https://play.google.com/store/apps/details?id={track_id}"


@mcp.tool
def get_playstore_app_name(track_id: str, lang_code: str = "en") -> dict:
    """Look up a Google Play app's name and details by its package id or Play Store URL.

    There is no name-to-id search for Google Play (unlike get_app_store_id
    for the App Store) — MobileAction only supports looking apps up by an
    already-known package id, e.g. "com.facebook.katana". If the user gives
    a Play Store link instead (e.g.
    "https://play.google.com/store/apps/details?id=com.facebook.katana"),
    pass it straight through — the id is extracted automatically. If the user
    only has an app name and no id/URL, ask them for the Play Store link
    rather than guessing the package id.

    Args:
        track_id: The app's Google Play package id (e.g. "com.facebook.katana")
            or a full Play Store app URL containing "?id=...".
        lang_code: Two-letter language code for the returned name/description, e.g. "en", "tr".
    """
    try:
        app = fetch_app_by_track_id(track_id, lang_code)
    except ToolError as exc:
        return to_error_response(exc)

    return {
        "app_id": app["trackId"],
        "name": app["name"],
        "url": _app_url(app["trackId"]),
    }


@mcp.tool
def get_playstore_app_names_batch(track_ids: str, lang_code: str = "en") -> dict:
    """Look up names/details for MULTIPLE Google Play package ids in one request.

    Call this ONCE with all ids comma-separated when you already have two or
    more package ids to resolve — most commonly the competitor list returned
    by get_playstore_apps_for_keyword. Do not call get_playstore_app_name once
    per id in a loop; this endpoint resolves all of them in a single request
    for a flat 1-credit cost regardless of how many ids are given.

    Ids MobileAction doesn't recognize are reported separately in
    "not_found_ids" rather than causing the whole call to fail.

    Args:
        track_ids: One or more Google Play package ids, comma-separated
            (e.g. "com.facebook.katana,com.duolingo"). Up to BATCH_LOOKUP_MAX_IDS
            (default 300, configurable via env var) per call.
        lang_code: Two-letter language code for the returned names, e.g. "en", "tr".
    """
    try:
        requested_ids, apps = fetch_apps_by_track_ids(track_ids, lang_code)
    except ToolError as exc:
        return to_error_response(exc)

    found_ids = {app["trackId"] for app in apps}

    return {
        "apps": [{"app_id": app["trackId"], "name": app["name"], "url": _app_url(app["trackId"])} for app in apps],
        "not_found_ids": [track_id for track_id in requested_ids if track_id not in found_ids],
    }
