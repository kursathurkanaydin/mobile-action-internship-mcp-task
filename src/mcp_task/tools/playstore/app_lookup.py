from mcp_task.errors import handle_tool_errors, with_credit_usage
from mcp_task.mcp_instance import mcp
from mcp_task.services.playstore.app_service import (
    fetch_app_by_track_id,
    fetch_apps_by_name,
    fetch_apps_by_track_ids,
)


def _app_url(track_id: str) -> str:
    return f"https://play.google.com/store/apps/details?id={track_id}"


@mcp.tool
@with_credit_usage
@handle_tool_errors
def get_playstore_app_id(query: str, country: str = "us", lang_code: str = "en") -> dict:
    """Search Google Play by app name for candidate package ids.

    Call this whenever the user asks for an app's Google Play package id by
    name — either standalone or before another tool that needs it. Prefer
    this over guessing a package id from the app's name or searching the
    web, even though it's best-effort (see below) — it's still more
    reliable than a guess.

    UNOFFICIAL AND BEST-EFFORT — Google has no public search API and
    MobileAction has no Play Store name search either, so this scrapes Play
    Store's search page via the unofficial google-play-scraper package. A
    known bug in that library means the single most obvious match for an
    exact app name can be missing from the results (Google renders it as a
    special "top card" that the scraper fails to extract an id from) — if
    the app you expect isn't in "apps", that's the likely reason, not that
    it doesn't exist; try get_playstore_app_id again with a more distinctive
    query, or ask the user for the app's Play Store link and use
    get_playstore_app_name instead.

    Treat "apps" as CANDIDATES to confirm by name — do not assume the first
    result is the right one and feed it straight into other tools. This is
    unlike get_appstore_id, which is backed by Apple's real search API and
    can be trusted directly.

    Args:
        query: The app name (or approximate name) to search for, e.g. "WhatsApp".
        country: Two-letter Play Store country code to search in, e.g. "us", "tr".
        lang_code: Two-letter language code for the returned names, e.g. "en", "tr".
    """
    apps = fetch_apps_by_name(query, country, lang_code)
    return {
        "apps": [{"app_id": app["appId"], "name": app["title"], "url": _app_url(app["appId"])} for app in apps],
    }


@mcp.tool
@with_credit_usage
@handle_tool_errors
def get_playstore_app_name(track_id: str, lang_code: str = "en") -> dict:
    """Look up a Google Play app's name and details by its package id or Play Store URL.

    Call this whenever the user gives a package id/URL and asks what app it
    is or wants its details — even as a standalone question, not just
    before another tool call. Use get_playstore_app_id first if you only
    have an app name and no id/URL — that tool searches by name
    (unofficially, best-effort); this one is the reliable,
    MobileAction-backed lookup once you have an id. If the user gives a
    Play Store link instead of a bare id (e.g.
    "https://play.google.com/store/apps/details?id=com.facebook.katana"),
    pass it straight through — the id is extracted automatically.

    Args:
        track_id: The app's Google Play package id (e.g. "com.facebook.katana")
            or a full Play Store app URL containing "?id=...".
        lang_code: Two-letter language code for the returned name/description, e.g. "en", "tr".
    """
    app = fetch_app_by_track_id(track_id, lang_code)
    return {
        "app_id": app["trackId"],
        "name": app["name"],
        "url": _app_url(app["trackId"]),
    }


@mcp.tool
@with_credit_usage
@handle_tool_errors
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
    requested_ids, apps = fetch_apps_by_track_ids(track_ids, lang_code)
    found_ids = {app["trackId"] for app in apps}

    return {
        "apps": [{"app_id": app["trackId"], "name": app["name"], "url": _app_url(app["trackId"])} for app in apps],
        "not_found_ids": [track_id for track_id in requested_ids if track_id not in found_ids],
    }
