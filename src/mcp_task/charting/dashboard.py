import json
from functools import lru_cache
from html import escape
from pathlib import Path
from statistics import mean

from mcp_task.charting.renderer import best_rank_series

_ACCENT_COLORS = ["#0A84FF", "#FF9F0A", "#30D158", "#FF375F", "#BF5AF2", "#64D2FF"]
_VENDOR_DIR = Path(__file__).parent / "vendor"
_DEVICES = ["IPHONE", "IPAD"]
_DEVICE_LABELS = {"IPHONE": "iPhone", "IPAD": "iPad"}


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
    """Build a self-contained, interactive HTML dashboard of keyword ranking history.

    Works for one app (a single-app ranking chart) or several (a comparison),
    just by the size of histories_by_app — the heading adapts automatically.
    Draws a live Chart.js line chart (rank per day, one series per app), with
    an iPhone/iPad toggle button that swaps the chart, stat cards, and summary
    table to that device's numbers — devices are kept separate rather than
    merged, since an app's iPhone and iPad ranks can differ a lot. Hovering a
    chart point shows its exact date/rank, legend entries can be clicked to
    hide a series, and the Chart.js library itself is embedded inline (no
    CDN) so the page works offline.
    """
    cards_by_device, rows_by_device, chart_data_by_device = {}, {}, {}
    for device in _DEVICES:
        cards, rows = [], []
        for index, (label, history) in enumerate(histories_by_app.items()):
            color = _ACCENT_COLORS[index % len(_ACCENT_COLORS)]
            stats = _summarize(history, device)
            cards.append(_render_stat_card(label, color, stats))
            rows.append(_render_table_row(label, color, stats))
        cards_by_device[device] = "".join(cards)
        rows_by_device[device] = "".join(rows)
        chart_data_by_device[device] = _build_chart_view(histories_by_app, device)

    default_device = _DEVICES[0]
    is_comparison = len(histories_by_app) > 1

    return _PAGE_TEMPLATE.format(
        keyword=escape(keyword),
        country_code=escape(country_code.upper()),
        start_date=escape(start_date),
        end_date=escape(end_date),
        heading="Keyword Ranking Comparison" if is_comparison else "Keyword Ranking",
        title_suffix="ranking comparison" if is_comparison else "ranking",
        device_toggle=_render_device_toggle(default_device),
        cards_sections=_render_device_sections("cards", cards_by_device, default_device),
        table_sections=_render_device_sections(
            "",
            rows_by_device,
            default_device,
            wrap_as_table=True,
            table_headers=["App", "Best rank", "Worst rank", "Average rank", "Days tracked"],
        ),
        css=_CSS,
        chartjs_source=_chartjs_source(),
        default_device=_safe_json(default_device),
        chart_data_by_device=_safe_json(chart_data_by_device),
    ).encode("utf-8")


def _build_chart_view(histories_by_app: dict[str, list[dict]], device: str) -> dict:
    """Build the {labels, datasets} Chart.js payload for one device."""
    series_by_app = {label: best_rank_series(history, device=device) for label, history in histories_by_app.items()}
    all_dates = sorted({entry_date for points in series_by_app.values() for entry_date, _ in points})

    datasets = []
    for index, (label, points) in enumerate(series_by_app.items()):
        color = _ACCENT_COLORS[index % len(_ACCENT_COLORS)]
        rank_by_date = dict(points)
        datasets.append(
            {
                "label": label,
                "borderColor": color,
                "backgroundColor": color,
                "spanGaps": False,
                # missing days become null -> Chart.js draws a gap instead of
                # snapping to zero or interpolating across them
                "data": [rank_by_date.get(entry_date) for entry_date in all_dates],
            }
        )

    return {"labels": [entry_date.strftime("%b %d") for entry_date in all_dates], "datasets": datasets}


def _summarize(history: list[dict], device: str) -> dict:
    points = best_rank_series(history, device=device)
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


def _render_device_toggle(default_device: str) -> str:
    buttons = "".join(
        f'<button type="button" class="device-btn{" active" if device == default_device else ""}" '
        f'data-device="{device}">{_DEVICE_LABELS[device]}</button>'
        for device in _DEVICES
    )
    return f'<div class="device-toggle">{buttons}</div>'


def _render_device_sections(
    css_class: str,
    content_by_device: dict[str, str],
    default_device: str,
    wrap_as_table: bool = False,
    table_headers: list[str] | None = None,
) -> str:
    """Render one <section> per device, hidden except for the default device.

    The inline JS toggles the `hidden` attribute on these when the user
    clicks the iPhone/iPad button, instead of re-rendering any markup.
    """
    sections = []
    for device, content in content_by_device.items():
        hidden_attr = "" if device == default_device else " hidden"
        class_attr = f' class="{css_class}"' if css_class else ""
        if wrap_as_table:
            header_cells = "".join(f"<th>{header}</th>" for header in table_headers or [])
            inner = f"<table><thead><tr>{header_cells}</tr></thead><tbody>{content}</tbody></table>"
        else:
            inner = content
        sections.append(f'<section{class_attr} data-device-section="{device}"{hidden_attr}>{inner}</section>')
    return "".join(sections)


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


def render_keyword_ranking_dashboard(
    rankings: list[dict],
    keywords: list[str],
    app_name: str,
    country_code: str,
    snapshot_date: str,
) -> bytes:
    """Build a self-contained, interactive HTML dashboard of one app's keyword rankings.

    Unlike the history dashboards this is a single-day snapshot across
    keywords, not a trend over time: one bar per ranked keyword (Chart.js bar
    chart, shortest bar = best rank), with an iPhone/iPad toggle like the
    other dashboards. A keyword the app doesn't rank for on a given device
    still gets a card/table row ("Not ranked") but is left out of that
    device's bar chart. Colors are assigned per keyword (not per rank
    position) so a keyword keeps the same color across both device views.
    """
    keyword_colors = {keyword: _ACCENT_COLORS[index % len(_ACCENT_COLORS)] for index, keyword in enumerate(keywords)}

    cards_by_device, rows_by_device, chart_data_by_device = {}, {}, {}
    for device in _DEVICES:
        rank_by_keyword = _keyword_rank_map(rankings, device)
        ranked_first = sorted(keywords, key=lambda kw: (rank_by_keyword.get(kw) is None, rank_by_keyword.get(kw, 0)))

        cards, rows = [], []
        for keyword in ranked_first:
            rank = rank_by_keyword.get(keyword)
            color = keyword_colors[keyword]
            cards.append(_render_keyword_card(keyword, color, rank))
            rows.append(_render_keyword_row(keyword, color, rank))
        cards_by_device[device] = "".join(cards)
        rows_by_device[device] = "".join(rows)

        chart_keywords = [kw for kw in ranked_first if rank_by_keyword.get(kw) is not None]
        chart_data_by_device[device] = {
            "labels": chart_keywords,
            "ranks": [rank_by_keyword[kw] for kw in chart_keywords],
            "colors": [keyword_colors[kw] for kw in chart_keywords],
        }

    default_device = _DEVICES[0]

    return _KEYWORD_PAGE_TEMPLATE.format(
        app_name=escape(app_name),
        country_code=escape(country_code.upper()),
        snapshot_date=escape(snapshot_date),
        device_toggle=_render_device_toggle(default_device),
        cards_sections=_render_device_sections("cards", cards_by_device, default_device),
        table_sections=_render_device_sections(
            "", rows_by_device, default_device, wrap_as_table=True, table_headers=["Keyword", "Rank"]
        ),
        css=_CSS,
        chartjs_source=_chartjs_source(),
        default_device=_safe_json(default_device),
        chart_data_by_device=_safe_json(chart_data_by_device),
    ).encode("utf-8")


def _keyword_rank_map(rankings: list[dict], device: str) -> dict[str, int]:
    """Map each keyword to its rank for one device, keeping the best if duplicated."""
    ranks: dict[str, int] = {}
    for entry in rankings:
        if entry.get("appKind") != device:
            continue
        rank = entry.get("rank")
        keyword = entry.get("keyword")
        if rank is None or keyword is None:
            continue
        if keyword not in ranks or rank < ranks[keyword]:
            ranks[keyword] = rank
    return ranks


def _render_keyword_card(keyword: str, color: str, rank: int | None) -> str:
    safe_keyword = escape(keyword)
    if rank is None:
        return (
            f'<div class="card" style="--accent:{color}">'
            f'<div class="card-label">{safe_keyword}</div>'
            f'<div class="card-empty">Not ranked</div>'
            f"</div>"
        )
    return (
        f'<div class="card" style="--accent:{color}">'
        f'<div class="card-label">{safe_keyword}</div>'
        f'<div class="card-rank">#{rank}</div>'
        f"</div>"
    )


def _render_keyword_row(keyword: str, color: str, rank: int | None) -> str:
    safe_keyword = escape(keyword)
    dot = f'<span class="dot" style="background:{color}"></span>'
    rank_cell = f"#{rank}" if rank is not None else "Not ranked"
    return f"<tr><td>{dot}{safe_keyword}</td><td>{rank_cell}</td></tr>"


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
[hidden] { display: none !important; }
body {
  margin: 0;
  padding: 2.5rem 1.5rem;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.page { max-width: 960px; margin: 0 auto; }
header h1 { margin: 0 0 0.25rem; font-size: 1.6rem; }
header .subtitle { margin: 0 0 1.5rem; color: var(--muted); font-size: 0.95rem; }
.device-toggle {
  display: inline-flex;
  gap: 2px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 3px;
  margin-bottom: 1.5rem;
}
.device-btn {
  border: none;
  background: transparent;
  color: var(--muted);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.4rem 1.1rem;
  border-radius: 999px;
  cursor: pointer;
}
.device-btn.active { background: var(--bg); color: var(--text); }
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
<title>"{keyword}" {title_suffix}</title>
<style>{css}</style>
<script>{chartjs_source}</script>
</head>
<body>
  <div class="page">
    <header>
      <h1>{heading}</h1>
      <p class="subtitle">"{keyword}" &middot; {country_code} App Store &middot; {start_date} &rarr; {end_date}</p>
    </header>

    {device_toggle}

    {cards_sections}

    <section class="chart-container">
      <canvas id="rankChart"></canvas>
    </section>

    {table_sections}
  </div>

  <script>
    const chartDataByDevice = {chart_data_by_device};
    let currentDevice = {default_device};

    const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const gridColor = isDarkMode ? '#3a3a3c' : '#e5e5ea';
    const textColor = isDarkMode ? '#98989d' : '#6e6e73';
    const fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

    function toDatasets(view) {{
      return view.datasets.map((dataset) => ({{
        ...dataset,
        borderWidth: 2,
        tension: 0.2,
        pointRadius: 3,
        pointHoverRadius: 6,
      }}));
    }}

    const chart = new Chart(document.getElementById('rankChart'), {{
      type: 'line',
      data: {{
        labels: chartDataByDevice[currentDevice].labels,
        datasets: toDatasets(chartDataByDevice[currentDevice]),
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

    function selectDevice(device) {{
      if (device === currentDevice || !chartDataByDevice[device]) return;
      currentDevice = device;

      const view = chartDataByDevice[device];
      chart.data.labels = view.labels;
      chart.data.datasets = toDatasets(view);
      chart.update();

      document.querySelectorAll('.device-btn').forEach((btn) => {{
        btn.classList.toggle('active', btn.dataset.device === device);
      }});
      document.querySelectorAll('[data-device-section]').forEach((section) => {{
        section.hidden = section.dataset.deviceSection !== device;
      }});
    }}

    document.querySelectorAll('.device-btn').forEach((btn) => {{
      btn.addEventListener('click', () => selectDevice(btn.dataset.device));
    }});
  </script>
</body>
</html>
"""

_KEYWORD_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{app_name} keyword rankings</title>
<style>{css}</style>
<script>{chartjs_source}</script>
</head>
<body>
  <div class="page">
    <header>
      <h1>Keyword Rankings</h1>
      <p class="subtitle">{app_name} &middot; {country_code} App Store &middot; {snapshot_date}</p>
    </header>

    {device_toggle}

    {cards_sections}

    <section class="chart-container">
      <canvas id="rankChart"></canvas>
    </section>

    {table_sections}
  </div>

  <script>
    const chartDataByDevice = {chart_data_by_device};
    let currentDevice = {default_device};

    const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const gridColor = isDarkMode ? '#3a3a3c' : '#e5e5ea';
    const textColor = isDarkMode ? '#98989d' : '#6e6e73';

    function toDataset(view) {{
      return {{
        label: 'Rank',
        data: view.ranks,
        backgroundColor: view.colors,
        borderRadius: 6,
        maxBarThickness: 48,
      }};
    }}

    const chart = new Chart(document.getElementById('rankChart'), {{
      type: 'bar',
      data: {{
        labels: chartDataByDevice[currentDevice].labels,
        datasets: [toDataset(chartDataByDevice[currentDevice])],
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: (context) => `Rank #${{context.parsed.y}}`,
            }},
          }},
        }},
        scales: {{
          x: {{
            grid: {{ display: false }},
            ticks: {{ color: textColor }},
          }},
          y: {{
            beginAtZero: true,
            title: {{ display: true, text: 'Rank (lower is better)', color: textColor }},
            grid: {{ color: gridColor }},
            ticks: {{ color: textColor, precision: 0 }},
          }},
        }},
      }},
    }});

    function selectDevice(device) {{
      if (device === currentDevice || !chartDataByDevice[device]) return;
      currentDevice = device;

      const view = chartDataByDevice[device];
      chart.data.labels = view.labels;
      chart.data.datasets = [toDataset(view)];
      chart.update();

      document.querySelectorAll('.device-btn').forEach((btn) => {{
        btn.classList.toggle('active', btn.dataset.device === device);
      }});
      document.querySelectorAll('[data-device-section]').forEach((section) => {{
        section.hidden = section.dataset.deviceSection !== device;
      }});
    }}

    document.querySelectorAll('.device-btn').forEach((btn) => {{
      btn.addEventListener('click', () => selectDevice(btn.dataset.device));
    }});
  </script>
</body>
</html>
"""
