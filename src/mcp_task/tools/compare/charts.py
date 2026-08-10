from fastmcp.exceptions import ToolError as FastMCPToolError

from mcp_task.charting.dashboard import COMPARE, render_dashboard_html, render_ranking_comparison_dashboard
from mcp_task.charting.server import publish_html
from mcp_task.errors import ToolError
from mcp_task.mcp_instance import mcp
from mcp_task.services.appstore.app_service import fetch_app_by_track_id
from mcp_task.services.compare.keyword_service import fetch_keyword_ranking, fetch_keyword_ranking_history


def _resolve_app_label(app_store_track_id: int, country_code: str) -> str:
    """Best-effort app name lookup for a comparison chart's title; falls back to the trackId.

    Resolved via the App Store side (Apple's free iTunes API), not Play
    Store (which would cost a credit) — either store's name is normally
    close enough for a chart title, and this is purely cosmetic.
    """
    try:
        app = fetch_app_by_track_id(app_store_track_id, country_code)
    except ToolError:
        return f"App {app_store_track_id}"
    return app.get("trackName") or f"App {app_store_track_id}"


def _rank_by_keyword(rankings: list[dict], keywords: list[str]) -> dict[str, int | None]:
    """Collapse raw {keyword, rank[, appKind]} entries to the best rank per keyword.

    Works for both App Store entries (multiple entries per keyword, one per
    device) and Play Store entries (one per keyword, no appKind at all) —
    either way, keeps the lowest (best) rank seen for each keyword.
    """
    best: dict[str, int] = {}
    for entry in rankings:
        keyword = entry.get("keyword")
        rank = entry.get("rank")
        if keyword is None or rank is None:
            continue
        if keyword not in best or rank < best[keyword]:
            best[keyword] = rank
    return {keyword: best.get(keyword) for keyword in keywords}


@mcp.tool
def plot_compare_stores_keyword_ranking(
    app_store_track_id: int,
    playstore_track_id: str,
    country_code: str,
    keywords: str,
    date: str | None = None,
) -> dict:
    """Show one app's App Store vs Google Play ranking for one or more keywords as a grouped bar chart.

    Same underlying data as compare_stores_keyword_ranking, drawn as a Chart.js bar
    chart (two bars per keyword — App Store, Play Store — shortest bar =
    best rank) instead of raw JSON. Needs the SAME app's id on both stores
    (see compare_stores_keyword_ranking's docstring for how to resolve them). This
    is a single-day snapshot, not a trend — use
    plot_compare_stores_keyword_ranking_history for that.

    Returns a clickable URL (served from a local, loopback-only HTTP server)
    that opens the interactive chart page in a browser.

    IMPORTANT: this URL is only useful if the user can see and click it, so
    you MUST paste the exact returned chart_url into your reply to the user
    as a markdown link, e.g. "[View the comparison chart]({chart_url})" —
    do not just say the chart is ready without including the link itself.

    Args:
        app_store_track_id: The app's numeric App Store id (e.g. 529479190 for Clash of Clans).
        playstore_track_id: The SAME app's Google Play package id (e.g. "com.supercell.clashofclans").
        country_code: Two-letter storefront code, used for both stores, e.g. "US", "TR".
        keywords: One or more keywords, comma-separated (e.g. "clan,war").
        date: Optional date in YYYY-MM-DD format. Defaults to the most recent
            available ranking day on each store if omitted.
    """
    try:
        data = fetch_keyword_ranking(app_store_track_id, playstore_track_id, country_code, keywords, date)
    except ToolError as exc:
        raise FastMCPToolError(exc.message) from exc

    if not data["app_store"] and not data["play_store"]:
        raise FastMCPToolError(f"No ranking data found on either store for the given keywords ({country_code}).")

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    app_store_ranks = _rank_by_keyword(data["app_store"], keyword_list)
    play_store_ranks = _rank_by_keyword(data["play_store"], keyword_list)
    non_empty = data["app_store"] or data["play_store"]
    snapshot_date = date or non_empty[0].get("date", "")[:10]
    app_name = _resolve_app_label(app_store_track_id, country_code)

    chart_html = render_ranking_comparison_dashboard(
        app_name, app_store_ranks, play_store_ranks, keyword_list, country_code, snapshot_date
    )
    chart_url = publish_html(chart_html)

    return {"chart_url": chart_url}


@mcp.tool
def plot_compare_stores_keyword_ranking_history(
    app_store_track_id: int,
    playstore_track_id: str,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Show one app's App Store vs Google Play ranking history for one keyword as an interactive chart.

    Same underlying data as compare_stores_keyword_ranking_history, drawn as a live
    Chart.js line chart — one line for App Store, one for Play Store. The
    App Store's iPhone/iPad ranks are pre-merged into a single
    best-rank-per-day line (no device toggle here), since this chart's
    whole point is comparing stores, not devices — a 3rd axis on top of
    store x time would be too busy to read. Needs the SAME app's id on both
    stores (see compare_stores_keyword_ranking's docstring for how to resolve
    them). The date range should not exceed 30 days per request.

    Returns a clickable URL (served from a local, loopback-only HTTP server)
    that opens the interactive chart page in a browser.

    IMPORTANT: this URL is only useful if the user can see and click it, so
    you MUST paste the exact returned chart_url into your reply to the user
    as a markdown link, e.g. "[View the comparison chart]({chart_url})" —
    do not just say the chart is ready without including the link itself.

    Args:
        app_store_track_id: The app's numeric App Store id (e.g. 529479190 for Clash of Clans).
        playstore_track_id: The SAME app's Google Play package id (e.g. "com.supercell.clashofclans").
        country_code: Two-letter storefront code, used for both stores, e.g. "US", "TR".
        keyword: A single keyword to compare ranking history for.
        start_date: History start date, inclusive, in YYYY-MM-DD format.
        end_date: History end date, inclusive, in YYYY-MM-DD format.
    """
    try:
        data = fetch_keyword_ranking_history(
            app_store_track_id, playstore_track_id, country_code, keyword, start_date, end_date
        )
    except ToolError as exc:
        raise FastMCPToolError(exc.message) from exc

    if not data["app_store"] and not data["play_store"]:
        raise FastMCPToolError(
            f"No ranking history found on either store for '{keyword}' ({country_code}, "
            f"{start_date} to {end_date})."
        )

    app_name = _resolve_app_label(app_store_track_id, country_code)
    histories_by_store = {"App Store": data["app_store"], "Play Store": data["play_store"]}
    chart_html = render_dashboard_html(
        histories_by_store,
        f"{app_name}: {keyword}",
        country_code,
        start_date,
        end_date,
        platform=COMPARE,
        series_label="Store",
    )
    chart_url = publish_html(chart_html)

    return {"chart_url": chart_url}
