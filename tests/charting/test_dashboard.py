import json
import re

from mcp_task.charting.dashboard import render_dashboard_html


def _entry(date: str, rank, device: str = "IPHONE"):
    return {"trackId": 1, "keyword": "strategy", "rank": rank, "countryCode": "US", "date": date, "appKind": device}


def _extract_json(text: str, var_name: str):
    match = re.search(rf"(?:const|let) {var_name} = (.+?);\n", text)
    assert match, f"could not find `const/let {var_name} = ...;` in the rendered page"
    return json.loads(match.group(1))


class TestRenderDashboardHtml:
    def test_returns_utf8_bytes_with_expected_header_info(self):
        histories = {"Clash of Clans": [_entry("2026-07-01T00:00:00", 12)]}
        html = render_dashboard_html(histories, "strategy", "US", "2026-07-01", "2026-07-10")

        assert isinstance(html, bytes)
        text = html.decode("utf-8")
        assert '"strategy"' in text
        assert "US App Store" in text
        assert "2026-07-01" in text and "2026-07-10" in text

    def test_chartjs_is_embedded_inline_not_via_cdn(self):
        histories = {"App A": [_entry("2026-07-01T00:00:00", 5)]}
        text = render_dashboard_html(histories, "kw", "US", "2026-07-01", "2026-07-01").decode()

        assert "cdn" not in text.lower()
        assert "Chart.js" in text  # the vendored library's own header comment

    def test_hidden_attribute_is_not_overridden_by_display_grid(self):
        # regression guard: elements with both [hidden] and a class that sets
        # `display` (like .cards { display: grid }) need an explicit
        # `[hidden] { display: none !important }` rule, or the hidden device
        # section renders visible anyway.
        text = render_dashboard_html(
            {"App A": [_entry("2026-07-01T00:00:00", 1)]}, "kw", "US", "2026-07-01", "2026-07-01"
        ).decode()
        assert "[hidden]" in text and "display: none !important" in text

    def test_device_toggle_buttons_present_with_iphone_active_by_default(self):
        text = render_dashboard_html(
            {"App A": [_entry("2026-07-01T00:00:00", 1)]}, "kw", "US", "2026-07-01", "2026-07-01"
        ).decode()

        assert '<button type="button" class="device-btn active" data-device="IPHONE">iPhone</button>' in text
        assert '<button type="button" class="device-btn" data-device="IPAD">iPad</button>' in text

    def test_only_default_device_section_is_visible_initially(self):
        text = render_dashboard_html(
            {"App A": [_entry("2026-07-01T00:00:00", 1)]}, "kw", "US", "2026-07-01", "2026-07-01"
        ).decode()

        assert 'data-device-section="IPHONE">' in text  # no `hidden` right after the attribute
        assert 'data-device-section="IPAD" hidden>' in text

    def test_chart_data_by_device_is_embedded_as_valid_json(self):
        histories = {
            "App A": [
                _entry("2026-07-01T00:00:00", 20, "IPHONE"),
                _entry("2026-07-02T00:00:00", 10, "IPHONE"),
                _entry("2026-07-01T00:00:00", 50, "IPAD"),
            ],
            "App B": [_entry("2026-07-01T00:00:00", 5, "IPHONE")],
        }
        text = render_dashboard_html(histories, "kw", "US", "2026-07-01", "2026-07-02").decode()

        chart_data = _extract_json(text, "chartDataByDevice")
        assert set(chart_data) == {"IPHONE", "IPAD"}

        iphone_view = chart_data["IPHONE"]
        assert iphone_view["labels"] == ["Jul 01", "Jul 02"]
        app_a = next(d for d in iphone_view["datasets"] if d["label"] == "App A")
        app_b = next(d for d in iphone_view["datasets"] if d["label"] == "App B")
        assert app_a["data"] == [20, 10]
        # App B only ranked on the first day -> second day is a gap (null), not 0 or interpolated
        assert app_b["data"] == [5, None]

        ipad_view = chart_data["IPAD"]
        assert ipad_view["labels"] == ["Jul 01"]
        assert {d["label"]: d["data"] for d in ipad_view["datasets"]} == {"App A": [50], "App B": [None]}

    def test_default_device_variable_matches_first_device(self):
        text = render_dashboard_html(
            {"App A": [_entry("2026-07-01T00:00:00", 1)]}, "kw", "US", "2026-07-01", "2026-07-01"
        ).decode()
        assert _extract_json(text, "currentDevice") == "IPHONE"

    def test_stat_card_shows_correct_best_worst_average_current(self):
        # ranks over 3 days: 20 -> 10 -> 13 (best=10, worst=20, avg=14.3, current=13)
        histories = {
            "App A": [
                _entry("2026-07-01T00:00:00", 20),
                _entry("2026-07-02T00:00:00", 10),
                _entry("2026-07-03T00:00:00", 13),
            ]
        }
        text = render_dashboard_html(histories, "kw", "US", "2026-07-01", "2026-07-03").decode()

        assert "#10" in text  # best
        assert "#20" in text  # worst
        assert "14.3" in text  # average
        assert "#13" in text  # current rank in the card

    def test_stat_cards_differ_between_devices(self):
        histories = {
            "App A": [
                _entry("2026-07-01T00:00:00", 5, "IPHONE"),
                _entry("2026-07-01T00:00:00", 90, "IPAD"),
            ]
        }
        text = render_dashboard_html(histories, "kw", "US", "2026-07-01", "2026-07-01").decode()

        iphone_section = text.split('data-device-section="IPHONE">', 1)[1].split("<section", 1)[0]
        ipad_section = text.split('data-device-section="IPAD" hidden>', 1)[1].split("<section", 1)[0]
        assert "#5" in iphone_section
        assert "#90" in ipad_section

    def test_improving_trend_marked_up_worsening_marked_down(self):
        improving = {"App A": [_entry("2026-07-01T00:00:00", 20), _entry("2026-07-02T00:00:00", 10)]}
        worsening = {"App B": [_entry("2026-07-01T00:00:00", 10), _entry("2026-07-02T00:00:00", 20)]}

        improving_html = render_dashboard_html(improving, "kw", "US", "2026-07-01", "2026-07-02").decode()
        worsening_html = render_dashboard_html(worsening, "kw", "US", "2026-07-01", "2026-07-02").decode()

        assert 'class="card-trend up"' in improving_html
        assert 'class="card-trend down"' in worsening_html

    def test_app_with_no_data_in_range_shows_empty_state_without_crashing(self):
        histories = {"No Data App": []}
        text = render_dashboard_html(histories, "kw", "US", "2026-07-01", "2026-07-05").decode()

        assert "No ranking data in this range" in text
        assert "No data" in text  # table row

    def test_no_dates_across_any_app_produces_empty_chart_arrays_for_both_devices(self):
        text = render_dashboard_html({"No Data App": []}, "kw", "US", "2026-07-01", "2026-07-05").decode()

        chart_data = _extract_json(text, "chartDataByDevice")
        for device_view in chart_data.values():
            assert device_view["labels"] == []
            assert device_view["datasets"] == [
                {"label": "No Data App", "borderColor": "#0A84FF", "backgroundColor": "#0A84FF",
                 "spanGaps": False, "data": []}
            ]


class TestRenderDashboardHtmlEscaping:
    def test_keyword_is_html_escaped_in_page_body(self):
        html = render_dashboard_html(
            {"App A": [_entry("2026-07-01T00:00:00", 1)]},
            "<script>alert(1)</script>",
            "US",
            "2026-07-01",
            "2026-07-01",
        ).decode()

        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html

    def test_app_label_is_html_escaped_in_cards_and_table(self):
        # The raw label legitimately appears inside the inline <script> JSON
        # blob (inert JS string data, not parsed as markup) so Chart.js can
        # show the real text — what matters is that the HTML *body* (cards,
        # table) only ever sees the escaped form.
        malicious_label = "<img src=x onerror=alert(1)>"
        html = render_dashboard_html(
            {malicious_label: [_entry("2026-07-01T00:00:00", 1)]},
            "kw",
            "US",
            "2026-07-01",
            "2026-07-01",
        ).decode()

        # everything in <body>, before the trailing inline <script> with the JSON data
        body = html.split("<body>", 1)[1].split("<script>", 1)[0]
        assert malicious_label not in body
        assert "&lt;img src=x onerror=alert(1)&gt;" in body

    def test_app_label_cannot_break_out_of_the_inline_script_tag(self):
        breakout_label = "</script><script>alert(1)</script>"
        html = render_dashboard_html(
            {breakout_label: [_entry("2026-07-01T00:00:00", 1)]},
            "kw",
            "US",
            "2026-07-01",
            "2026-07-01",
        ).decode()

        # the raw sequence must never appear literally, or a browser's HTML
        # parser would close the <script> block early
        assert "</script><script>alert(1)</script>" not in html

        # but the JSON must still round-trip to the original label so Chart.js
        # renders the real (HTML-escaped-for-display) legend text correctly
        chart_data = _extract_json(html, "chartDataByDevice")
        assert chart_data["IPHONE"]["datasets"][0]["label"] == breakout_label
