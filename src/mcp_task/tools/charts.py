from fastmcp.exceptions import ToolError as FastMCPToolError

from mcp_task.charting.dashboard import render_dashboard_html, render_keyword_ranking_dashboard
from mcp_task.charting.server import publish_html
from mcp_task.errors import ToolError
from mcp_task.mcp_instance import mcp
from mcp_task.services.app_service import fetch_app_by_track_id
from mcp_task.services.keyword_service import fetch_keyword_ranking, fetch_keyword_ranking_history
from mcp_task.validation import require_track_id_list


def _resolve_app_label(track_id: int, country_code: str) -> str:
    """Best-effort app name lookup for a chart/table label; falls back to the track id."""
    try:
        app = fetch_app_by_track_id(track_id, country_code)
    except ToolError:
        return f"App {track_id}"
    return app.get("trackName") or f"App {track_id}"


@mcp.tool
def plot_keyword_ranking(
    track_id: int,
    country_code: str,
    keywords: str,
    date: str | None = None,
) -> dict:
    """Show ONE app's current App Store ranking for one or more keywords as an interactive chart.

    Same underlying data as get_keyword_ranking, drawn as a Chart.js bar chart
    (one bar per keyword, shortest bar = best rank) with an iPhone/iPad toggle
    button and a per-keyword breakdown table, instead of raw JSON. Use this
    when the user wants to *see* how an app ranks across several keywords at
    a glance (e.g. "chart app X's ranking for these keywords", "visualize app
    X's keyword rankings"), as opposed to a single keyword's trend over time
    (use plot_keyword_ranking_history for that) or comparing apps (use
    compare_keyword_ranking_history for that). This is a single-day snapshot,
    not a trend.

    Returns a clickable URL (served from a local, loopback-only HTTP server)
    that opens the interactive chart page in a browser.

    IMPORTANT: this URL is only useful if the user can see and click it, so
    you MUST paste the exact returned chart_url into your reply to the user
    as a markdown link, e.g. "[View the keyword ranking chart]({chart_url})"
    — do not just say the chart is ready without including the link itself.

    Args:
        track_id: The app's numeric App Store id (e.g. 529479190 for Clash of Clans).
        country_code: Two-letter App Store country/storefront code, e.g. "US", "TR".
        keywords: One or more keywords, comma-separated (e.g. "ticket,event,concert").
        date: Optional date in YYYY-MM-DD format. Defaults to the most recent
            available ranking day if omitted.
    """
    try:
        rankings = fetch_keyword_ranking(track_id, country_code, keywords, date)
    except ToolError as exc:
        raise FastMCPToolError(exc.message) from exc

    if not rankings:
        raise FastMCPToolError(f"No ranking data found for the given keywords (track {track_id}, {country_code}).")

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    app_name = _resolve_app_label(track_id, country_code)
    snapshot_date = date or rankings[0].get("date", "")[:10]

    chart_html = render_keyword_ranking_dashboard(rankings, keyword_list, app_name, country_code, snapshot_date)
    chart_url = publish_html(chart_html)

    return {"chart_url": chart_url}


@mcp.tool
def plot_keyword_ranking_history(
    track_id: int,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Render ONE app's App Store ranking history for a keyword as an interactive chart.

    Same underlying data as get_keyword_ranking_history, drawn as a live
    Chart.js line chart with an iPhone/iPad toggle button (hover a point for
    its exact date/rank) instead of raw JSON. Use this when the user wants to
    *see* a single app's trend rather than read numbers (e.g. "graph app X's
    rank for keyword Y over the last month", "show me a chart of the ranking
    history"). The date range should not exceed 30 days per request.

    Do NOT call this once per app to compare multiple apps — if the user gives
    two or more apps to compare (vs, side-by-side, "which one ranks better"),
    use compare_keyword_ranking_history instead; it produces one combined
    dashboard rather than separate charts you'd have to describe yourself.

    Returns a clickable URL (served from a local, loopback-only HTTP server)
    that opens the interactive chart page in a browser.

    IMPORTANT: this URL is only useful if the user can see and click it, so
    you MUST paste the exact returned chart_url into your reply to the user
    as a markdown link, e.g. "[View the ranking chart]({chart_url})" — do not
    just say the chart is ready without including the link itself.

    Args:
        track_id: The app's numeric App Store id (e.g. 529479190 for Clash of Clans).
        country_code: Two-letter App Store country/storefront code, e.g. "US", "TR".
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
            f"No ranking history found for '{keyword}' (track {track_id}, {country_code}, "
            f"{start_date} to {end_date})."
        )

    label = _resolve_app_label(track_id, country_code)
    chart_html = render_dashboard_html({label: history}, keyword, country_code, start_date, end_date)
    chart_url = publish_html(chart_html)

    return {"chart_url": chart_url}


@mcp.tool
def compare_keyword_ranking_history(
    track_ids: str,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Compare TWO OR MORE apps' App Store ranking history for one keyword as an HTML dashboard.

    This is the tool to call whenever the user names two or more apps and
    wants their ranking for a keyword compared, e.g. "compare app X and app Y's
    ranking for keyword Z", "app X vs app Y for keyword Z", "how do my top 3
    competitors rank for this keyword", "build/show me a dashboard comparing
    these apps' rankings" — with or without the word "dashboard" or "chart"
    in the request. For a single app's trend, use plot_keyword_ranking_history
    or get_keyword_ranking_history instead.

    Call this ONCE with all the apps' track_ids together — do not call
    get_keyword_ranking_history or plot_keyword_ranking_history separately for
    each app and combine the results yourself; this tool fetches every app's
    history and renders the comparison chart + dashboard in one step, which
    those single-app tools cannot do.

    Fetches each app's ranking history, collapses iPhone/iPad to a single best
    rank per day (comparing multiple apps' devices at once gets too busy), and
    renders a dashboard: an interactive line chart (toggle apps via the legend,
    hover a point for its exact date/rank) plus a per-app stat card and summary
    table (best/worst/average rank, current trend). The date range should not
    exceed 30 days per request; between 2 and 5 apps are supported (each app
    costs a separate MobileAction API request, so this is capped to limit
    credit usage per call).

    Returns a clickable URL (served from a local, loopback-only HTTP server)
    that opens the dashboard in a browser.

    IMPORTANT: this URL is only useful if the user can see and click it, so
    you MUST paste the exact returned dashboard_url into your reply to the
    user as a markdown link, e.g. "[View the comparison dashboard]({dashboard_url})"
    — do not just say the dashboard is ready without including the link itself.

    Args:
        track_ids: Two to five App Store ids, comma-separated (e.g. "529479190,553834731").
        country_code: Two-letter App Store country/storefront code, e.g. "US", "TR".
        keyword: A single keyword to compare ranking history for.
        start_date: History start date, inclusive, in YYYY-MM-DD format.
        end_date: History end date, inclusive, in YYYY-MM-DD format.
    """
    try:
        ids = require_track_id_list(track_ids)

        histories_by_app = {}
        for track_id in ids:
            label = _resolve_app_label(track_id, country_code)
            histories_by_app[label] = fetch_keyword_ranking_history(
                track_id, country_code, keyword, start_date, end_date
            )
    except ToolError as exc:
        raise FastMCPToolError(exc.message) from exc

    if not any(histories_by_app.values()):
        raise FastMCPToolError(
            f"No ranking history found for '{keyword}' for any of the given apps "
            f"({country_code}, {start_date} to {end_date})."
        )

    dashboard_html = render_dashboard_html(histories_by_app, keyword, country_code, start_date, end_date)
    dashboard_url = publish_html(dashboard_html)

    return {"dashboard_url": dashboard_url}
