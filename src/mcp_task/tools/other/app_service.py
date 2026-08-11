from mcp_task.errors import handle_tool_errors, with_credit_usage
from mcp_task.mcp_instance import mcp
from mcp_task.services.other.app_service import fetch_app_match


@mcp.tool
@with_credit_usage
@handle_tool_errors
def get_app_match(store: str, track_id: str) -> dict:
    """Find an app's id in the OPPOSITE store (App Store <-> Google Play), via MobileAction's official pairing.

    Call this whenever the user asks for an app's id/package name on the
    OTHER store, given an id on one store — either as a standalone question
    ("what's the Google Play id for App Store id 553834731?") or as a first
    step before another tool that needs the second id (e.g.
    compare_stores_keyword_ranking). Always call this tool rather than
    guessing a package id from the app's name or searching the web:
    App Store and Play Store ids are unrelated strings with no formula
    connecting them, and MobileAction's own pairing is the authoritative
    source — a wrong guess would silently pair the wrong app.

    Args:
        store: Which store track_id belongs to: "ios" (App Store) or "play" (Google Play).
        track_id: The app's id on that store — a numeric App Store trackId
            (e.g. "284882215") if store is "ios", or a Google Play package
            name (e.g. "com.facebook.katana") if store is "play".
    """
    matching_track_id = fetch_app_match(store, track_id)
    return {"matching_track_id": matching_track_id}
