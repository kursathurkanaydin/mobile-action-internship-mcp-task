from fastmcp.exceptions import ToolError as FastMCPToolError

from mcp_task.charting.renderer import render_ranking_history_chart
from mcp_task.charting.server import publish_chart
from mcp_task.errors import ToolError
from mcp_task.mcp_instance import mcp
from mcp_task.tools.keyword_services import fetch_keyword_ranking_history


@mcp.tool
def plot_keyword_ranking_history(
    track_id: int,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Render a line chart of an app's App Store ranking history for a keyword.

    Same underlying data as get_keyword_ranking_history, plotted as rank-over-time
    (one line per device: iPhone/iPad) instead of raw JSON. Use this when the user
    wants to *see* a trend rather than read numbers (e.g. "graph app X's rank for
    keyword Y over the last month", "show me a chart of the ranking history").
    The date range should not exceed 30 days per request.

    Returns a clickable URL (served from a local, loopback-only HTTP server)
    that opens the chart PNG in a browser.

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

    png_bytes = render_ranking_history_chart(history, keyword, country_code, track_id)
    chart_url = publish_chart(png_bytes)

    return {"chart_url": chart_url}
