import io
from collections import defaultdict
from datetime import datetime

import matplotlib

matplotlib.use("Agg")  # headless: we only ever render to an in-memory PNG buffer

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

_DEVICE_STYLE = {
    "IPHONE": {"label": "iPhone", "color": "#0A84FF"},
    "IPAD": {"label": "iPad", "color": "#FF9F0A"},
}


def render_ranking_history_chart(history: list[dict], keyword: str, country_code: str, track_id: int) -> bytes:
    """Render an app's App Store keyword ranking history as a PNG line chart.

    One line per device (iPhone/iPad), rank inverted so the best rank sits at
    the top. Expects the raw {rank, date, appKind} entries returned by the
    MobileAction ranking-history endpoint.
    """
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
    return buffer.getvalue()
