from fastmcp.exceptions import ToolError as FastMCPToolError

from mcp_task.charting.dashboard import PLAY_STORE, render_dashboard_html
from mcp_task.charting.server import publish_html
from mcp_task.errors import ToolError, with_credit_usage
from mcp_task.mcp_instance import mcp
from mcp_task.services.playstore.app_service import fetch_app_by_track_id
from mcp_task.services.playstore.keyword_service import (
    fetch_keyword_ranking_history,
    fetch_keyword_ranking_history_multi,
)


def _resolve_app_label(track_id: str, lang_code: str = "en") -> str:
    """Best-effort app name lookup for a chart/table label; falls back to the track id."""
    try:
        app = fetch_app_by_track_id(track_id, lang_code)
    except ToolError:
        return track_id
    return app.get("name") or track_id


@mcp.tool
@with_credit_usage
def plot_playstore_keyword_ranking_history(
    track_id: str,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Render ONE Google Play app's ranking history for a SINGLE keyword as an interactive chart.

    Same underlying data as get_playstore_keyword_ranking_history, drawn as a
    live Chart.js line chart (hover a point for its exact date/rank) instead
    of raw JSON. There's no iPhone/iPad toggle here, unlike the App Store
    dashboards — Google Play history entries have no device dimension at all.

    Only call this tool if the request contains an EXPLICIT visual keyword:
    "chart", "graph", "plot", "visualize", "draw", or "show me a
    chart/graph/graphic" (e.g. "graph app X's ranking for this keyword on
    Google Play", "show me a chart of the ranking history"). Generic
    trend/change wording with NO such keyword — "how has app X's rank
    changed", "nasıl değişmiş", "what's the trend" — is NOT enough by
    itself; that default case is get_playstore_keyword_ranking_history's
    job, not this tool's. The date range should not exceed 30 days per
    request.

    For MULTIPLE keywords on one app, use
    plot_playstore_keyword_ranking_history_multi instead — it fetches every
    keyword itself and renders one combined chart (one line per keyword),
    rather than you calling this tool once per keyword.

    Returns a clickable URL (served from a local, loopback-only HTTP server)
    that opens the interactive chart page in a browser.

    IMPORTANT: this URL is only useful if the user can see and click it, so
    you MUST paste the exact returned chart_url into your reply to the user
    as a markdown link, e.g. "[View the ranking chart]({chart_url})" — do not
    just say the chart is ready without including the link itself.

    Args:
        track_id: The app's Google Play package name (e.g. "com.supercell.clashofclans").
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
        keyword: A single keyword to chart the ranking history for.
        start_date: History start date, inclusive, in YYYY-MM-DD format.
        end_date: History end date, inclusive, in YYYY-MM-DD format.
    """
    try:
        history = fetch_keyword_ranking_history(track_id, country_code, keyword, start_date, end_date)
    except ToolError as exc:
        raise FastMCPToolError(exc.message) from exc

    if not history:
        raise FastMCPToolError(
            f"No ranking history found for '{keyword}' ({track_id}, {country_code}, "
            f"{start_date} to {end_date})."
        )

    app_name = _resolve_app_label(track_id)
    chart_html = render_dashboard_html(
        {app_name: history}, keyword, country_code, start_date, end_date, platform=PLAY_STORE
    )
    chart_url = publish_html(chart_html)

    return {"chart_url": chart_url}


@mcp.tool
@with_credit_usage
def plot_playstore_keyword_ranking_history_multi(
    track_id: str,
    country_code: str,
    keywords: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Render ONE Google Play app's ranking history for MULTIPLE keywords as an interactive chart.

    Same underlying data as get_playstore_keyword_ranking_history_multi,
    drawn as a live Chart.js line chart (one line per keyword, hover a point
    for its exact date/rank) instead of raw JSON. There's no iPhone/iPad
    toggle here, unlike the App Store dashboards — Google Play history
    entries have no device dimension at all, so this is always a single
    merged view.

    Only call this tool if the request contains an EXPLICIT visual keyword:
    "chart", "graph", "plot", "visualize", "draw", or "show me a
    chart/graph/graphic" (e.g. "graph app X's ranking for these keywords on
    Google Play"). Generic trend/change wording with no such keyword stays
    with get_playstore_keyword_ranking_history_multi instead.

    Do NOT call this once per keyword — pass all the keywords comma-separated
    in one call; this tool fetches every keyword's history itself (one
    MobileAction request per keyword, since the history endpoint has no
    batch-keyword mode) and renders them as one combined chart. The date
    range should not exceed 30 days per request; up to 10 keywords are
    supported.

    Returns a clickable URL (served from a local, loopback-only HTTP server)
    that opens the interactive chart page in a browser.

    IMPORTANT: this URL is only useful if the user can see and click it, so
    you MUST paste the exact returned chart_url into your reply to the user
    as a markdown link, e.g. "[View the ranking chart]({chart_url})" — do not
    just say the chart is ready without including the link itself.

    Args:
        track_id: The app's Google Play package name (e.g. "com.supercell.clashofclans").
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
        keywords: Two or more keywords, comma-separated (e.g. "game,strategy,clan,war").
        start_date: History start date, inclusive, in YYYY-MM-DD format.
        end_date: History end date, inclusive, in YYYY-MM-DD format.
    """
    try:
        histories_by_keyword = fetch_keyword_ranking_history_multi(
            track_id, country_code, keywords, start_date, end_date
        )
    except ToolError as exc:
        raise FastMCPToolError(exc.message) from exc

    if not any(histories_by_keyword.values()):
        raise FastMCPToolError(
            f"No ranking history found for any of the given keywords ({track_id}, {country_code}, "
            f"{start_date} to {end_date})."
        )

    app_name = _resolve_app_label(track_id)
    dashboard_html = render_dashboard_html(
        histories_by_keyword,
        app_name,
        country_code,
        start_date,
        end_date,
        platform=PLAY_STORE,
        series_label="Keyword",
    )
    chart_url = publish_html(dashboard_html)

    return {"chart_url": chart_url}
