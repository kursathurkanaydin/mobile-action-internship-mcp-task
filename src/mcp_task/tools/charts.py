import io
from collections import defaultdict
from datetime import datetime

import matplotlib

matplotlib.use("Agg")  # headless: we only ever render to an in-memory PNG buffer

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from fastmcp.exceptions import ToolError

from mcp_task.chart_server import publish_chart
from mcp_task.errors import ToolInputError
from mcp_task.mcp_instance import mcp
from mcp_task.tools.keyword_services import fetch_keyword_ranking_history

_DEVICE_STYLE = {
    "IPHONE": {"label": "iPhone", "color": "#0A84FF"},
    "IPAD": {"label": "iPad", "color": "#FF9F0A"},
}


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
    except ToolInputError as exc:
        raise ToolError(exc.message) from exc

    if not history:
        raise ToolError(
            f"No ranking history found for '{keyword}' (track {track_id}, {country_code}, "
            f"{start_date} to {end_date})."
        )

    series: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    for entry in history:
        rank = entry.get("rank")
        if rank is None:
            continue
        device = entry.get("appKind", "UNKNOWN")
        series[device].append((datetime.fromisoformat(entry["date"]), rank))

    for points in series.values():
        points.sort(key=lambda point: point[0])

    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)

    for device in sorted(series):
        style = _DEVICE_STYLE.get(device, {"label": device, "color": "#8E8E93"})
        dates = [point[0] for point in series[device]]
        ranks = [point[1] for point in series[device]]
        ax.plot(
            dates,
            ranks,
            marker="o",
            markersize=4,
            linewidth=2,
            color=style["color"],
            label=style["label"],
        )

    ax.invert_yaxis()  # rank 1 is the best rank, so it should sit at the top
    ax.set_title(
        f'"{keyword}" ranking — {country_code.upper()} App Store (track {track_id})',
        fontsize=13,
        fontweight="bold",
        pad=14,
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Rank (lower is better)")
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)

    chart_url = publish_chart(buffer.getvalue())

    return {"chart_url": chart_url}
