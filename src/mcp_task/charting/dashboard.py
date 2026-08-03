import base64
from html import escape
from statistics import mean

from mcp_task.charting.renderer import best_rank_series

_ACCENT_COLORS = ["#0A84FF", "#FF9F0A", "#30D158", "#FF375F", "#BF5AF2", "#64D2FF"]


def render_dashboard_html(
    histories_by_app: dict[str, list[dict]],
    chart_png: bytes,
    keyword: str,
    country_code: str,
    start_date: str,
    end_date: str,
) -> bytes:
    """Build a self-contained HTML dashboard comparing keyword ranking history across apps.

    Embeds the pre-rendered comparison chart as a data URI (no separate image
    file to serve) and adds a per-app stat card + summary table below it,
    computed from the same best_rank_series numbers the chart was drawn from.
    """
    chart_data_uri = base64.b64encode(chart_png).decode()

    cards, rows = [], []
    for index, (label, history) in enumerate(histories_by_app.items()):
        color = _ACCENT_COLORS[index % len(_ACCENT_COLORS)]
        stats = _summarize(history)
        cards.append(_render_stat_card(label, color, stats))
        rows.append(_render_table_row(label, color, stats))

    return _PAGE_TEMPLATE.format(
        keyword=escape(keyword),
        country_code=escape(country_code.upper()),
        start_date=escape(start_date),
        end_date=escape(end_date),
        cards="".join(cards),
        rows="".join(rows),
        chart_data_uri=chart_data_uri,
        css=_CSS,
    ).encode("utf-8")


def _summarize(history: list[dict]) -> dict:
    points = best_rank_series(history)
    if not points:
        return {"days": 0}

    ranks = [rank for _, rank in points]
    return {
        "days": len(points),
        "best": min(ranks),
        "worst": max(ranks),
        "average": round(mean(ranks), 1),
        "current": ranks[-1],
        "trend": ranks[0] - ranks[-1],  # positive = improved (rank number went down)
    }


def _render_stat_card(label: str, color: str, stats: dict) -> str:
    safe_label = escape(label)
    if stats["days"] == 0:
        return (
            f'<div class="card" style="--accent:{color}">'
            f'<div class="card-label">{safe_label}</div>'
            f'<div class="card-empty">No ranking data in this range</div>'
            f"</div>"
        )

    trend = stats["trend"]
    trend_class = "up" if trend > 0 else "down" if trend < 0 else "flat"
    trend_symbol = "▲" if trend > 0 else "▼" if trend < 0 else "–"
    return (
        f'<div class="card" style="--accent:{color}">'
        f'<div class="card-label">{safe_label}</div>'
        f'<div class="card-rank">#{stats["current"]}</div>'
        f'<div class="card-trend {trend_class}">{trend_symbol} {abs(trend)} over {stats["days"]}d</div>'
        f'<div class="card-best">Best: #{stats["best"]}</div>'
        f"</div>"
    )


def _render_table_row(label: str, color: str, stats: dict) -> str:
    safe_label = escape(label)
    dot = f'<span class="dot" style="background:{color}"></span>'
    if stats["days"] == 0:
        return f"<tr><td>{dot}{safe_label}</td><td colspan='4'>No data</td></tr>"
    return (
        f"<tr><td>{dot}{safe_label}</td>"
        f'<td>#{stats["best"]}</td><td>#{stats["worst"]}</td>'
        f'<td>#{stats["average"]}</td><td>{stats["days"]}</td></tr>'
    )


_CSS = """
:root {
  color-scheme: light dark;
  --bg: #f5f5f7;
  --surface: #ffffff;
  --text: #1d1d1f;
  --muted: #6e6e73;
  --border: #e5e5ea;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1c1e;
    --surface: #2c2c2e;
    --text: #f5f5f7;
    --muted: #98989d;
    --border: #3a3a3c;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 2.5rem 1.5rem;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.page { max-width: 960px; margin: 0 auto; }
header h1 { margin: 0 0 0.25rem; font-size: 1.6rem; }
header .subtitle { margin: 0 0 2rem; color: var(--muted); font-size: 0.95rem; }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: 3px solid var(--accent);
  border-radius: 12px;
  padding: 1rem 1.1rem;
}
.card-label { font-size: 0.85rem; color: var(--muted); margin-bottom: 0.4rem; }
.card-rank { font-size: 1.6rem; font-weight: 700; }
.card-trend { font-size: 0.85rem; margin-top: 0.3rem; }
.card-trend.up { color: #30d158; }
.card-trend.down { color: #ff453a; }
.card-trend.flat { color: var(--muted); }
.card-best { font-size: 0.8rem; color: var(--muted); margin-top: 0.5rem; }
.card-empty { font-size: 0.85rem; color: var(--muted); }
.chart {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 2rem;
}
.chart img { width: 100%; height: auto; display: block; border-radius: 6px; }
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}
th, td { text-align: left; padding: 0.65rem 1rem; font-size: 0.9rem; }
thead th { color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border); }
tbody tr:not(:last-child) td { border-bottom: 1px solid var(--border); }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 0.5rem; }
"""

_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>"{keyword}" ranking comparison</title>
<style>{css}</style>
</head>
<body>
  <div class="page">
    <header>
      <h1>Keyword Ranking Comparison</h1>
      <p class="subtitle">"{keyword}" &middot; {country_code} App Store &middot; {start_date} &rarr; {end_date}</p>
    </header>

    <section class="cards">{cards}</section>

    <section class="chart">
      <img src="data:image/png;base64,{chart_data_uri}" alt="Ranking comparison chart">
    </section>

    <section>
      <table>
        <thead>
          <tr><th>App</th><th>Best rank</th><th>Worst rank</th><th>Average rank</th><th>Days tracked</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""
