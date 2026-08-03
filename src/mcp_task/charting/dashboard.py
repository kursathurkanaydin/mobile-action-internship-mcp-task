import json
from functools import lru_cache
from html import escape
from pathlib import Path
from statistics import mean

from mcp_task.charting.renderer import best_rank_series

_ACCENT_COLORS = ["#0A84FF", "#FF9F0A", "#30D158", "#FF375F", "#BF5AF2", "#64D2FF"]
_VENDOR_DIR = Path(__file__).parent / "vendor"


@lru_cache(maxsize=1)
def _chartjs_source() -> str:
    """Chart.js UMD build, vendored locally so the dashboard needs no CDN/network access."""
    return (_VENDOR_DIR / "chart.umd.min.js").read_text(encoding="utf-8")


def _safe_json(value) -> str:
    """json.dumps that's safe to inline inside a <script> tag.

    A raw "</script" substring in an app label or date would otherwise close
    the script block early and let the rest be parsed as HTML.
    """
    return json.dumps(value).replace("</", "<\\/")


def render_dashboard_html(
    histories_by_app: dict[str, list[dict]],
    keyword: str,
    country_code: str,
    start_date: str,
    end_date: str,
) -> bytes:
    """Build a self-contained, interactive HTML dashboard comparing keyword ranking history.

    Draws the comparison as a live Chart.js line chart (rank per day, one
    series per app) instead of a static image: series can be toggled from the
    legend, hovering a point shows its exact date/rank, and the Chart.js
    library itself is embedded inline (no CDN) so the page works offline.
    Adds a per-app stat card + summary table below it, computed from the same
    best_rank_series numbers the chart is drawn from.
    """
    series_by_app = {label: best_rank_series(history) for label, history in histories_by_app.items()}
    all_dates = sorted({entry_date for points in series_by_app.values() for entry_date, _ in points})

    cards, rows, datasets = [], [], []
    for index, (label, history) in enumerate(histories_by_app.items()):
        color = _ACCENT_COLORS[index % len(_ACCENT_COLORS)]
        stats = _summarize(history)
        cards.append(_render_stat_card(label, color, stats))
        rows.append(_render_table_row(label, color, stats))
        datasets.append(_build_dataset(label, color, series_by_app[label], all_dates))

    return _PAGE_TEMPLATE.format(
        keyword=escape(keyword),
        country_code=escape(country_code.upper()),
        start_date=escape(start_date),
        end_date=escape(end_date),
        cards="".join(cards),
        rows="".join(rows),
        css=_CSS,
        chartjs_source=_chartjs_source(),
        chart_labels=_safe_json([entry_date.strftime("%b %d") for entry_date in all_dates]),
        chart_datasets=_safe_json(datasets),
    ).encode("utf-8")


def _build_dataset(label: str, color: str, points: list[tuple], all_dates: list) -> dict:
    """Align one app's (date, rank) points onto the shared all_dates axis.

    Days the app has no ranking for become null, which Chart.js renders as a
    gap in the line rather than snapping to zero or interpolating.
    """
    rank_by_date = dict(points)
    return {
        "label": label,
        "borderColor": color,
        "backgroundColor": color,
        "spanGaps": False,
        "data": [rank_by_date.get(entry_date) for entry_date in all_dates],
    }


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
.chart-container {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  height: 420px;
  position: relative;
}
canvas { width: 100% !important; height: 100% !important; }
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
<script>{chartjs_source}</script>
</head>
<body>
  <div class="page">
    <header>
      <h1>Keyword Ranking Comparison</h1>
      <p class="subtitle">"{keyword}" &middot; {country_code} App Store &middot; {start_date} &rarr; {end_date}</p>
    </header>

    <section class="cards">{cards}</section>

    <section class="chart-container">
      <canvas id="rankChart"></canvas>
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

  <script>
    const labels = {chart_labels};
    const datasets = {chart_datasets};
    const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const gridColor = isDarkMode ? '#3a3a3c' : '#e5e5ea';
    const textColor = isDarkMode ? '#98989d' : '#6e6e73';
    const fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

    new Chart(document.getElementById('rankChart'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: datasets.map((dataset) => ({{
          ...dataset,
          borderWidth: 2,
          tension: 0.2,
          pointRadius: 3,
          pointHoverRadius: 6,
        }})),
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: textColor, usePointStyle: true, padding: 16, font: {{ family: fontFamily }} }},
          }},
          tooltip: {{
            callbacks: {{
              label: (context) =>
                context.parsed.y === null ? null : `${{context.dataset.label}}: Rank #${{context.parsed.y}}`,
            }},
          }},
        }},
        scales: {{
          x: {{
            grid: {{ color: gridColor }},
            ticks: {{ color: textColor }},
          }},
          y: {{
            reverse: true,
            title: {{ display: true, text: 'Rank (lower is better)', color: textColor }},
            grid: {{ color: gridColor }},
            ticks: {{ color: textColor, precision: 0 }},
          }},
        }},
      }},
    }});
  </script>
</body>
</html>
"""
