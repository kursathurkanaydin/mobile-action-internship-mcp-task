from mcp_task.charting.dashboard import render_dashboard_html

_FAKE_PNG = b"not-a-real-png-but-thats-fine-for-this-test"


def _entry(date: str, rank):
    return {"trackId": 1, "keyword": "strategy", "rank": rank, "countryCode": "US", "date": date, "appKind": "IPHONE"}


class TestRenderDashboardHtml:
    def test_returns_utf8_bytes_with_expected_header_info(self):
        histories = {"Clash of Clans": [_entry("2026-07-01T00:00:00", 12)]}
        html = render_dashboard_html(histories, _FAKE_PNG, "strategy", "US", "2026-07-01", "2026-07-10")

        assert isinstance(html, bytes)
        text = html.decode("utf-8")
        assert '"strategy"' in text
        assert "US App Store" in text
        assert "2026-07-01" in text and "2026-07-10" in text

    def test_embeds_chart_as_base64_data_uri(self):
        import base64

        histories = {"App A": [_entry("2026-07-01T00:00:00", 5)]}
        html = render_dashboard_html(histories, _FAKE_PNG, "kw", "US", "2026-07-01", "2026-07-05")
        text = html.decode("utf-8")

        expected_data_uri = base64.b64encode(_FAKE_PNG).decode()
        assert f"data:image/png;base64,{expected_data_uri}" in text

    def test_stat_card_shows_correct_best_worst_average_current(self):
        # ranks over 3 days: 20 -> 10 -> 13 (best=10, worst=20, avg=14.3, current=13)
        histories = {
            "App A": [
                _entry("2026-07-01T00:00:00", 20),
                _entry("2026-07-02T00:00:00", 10),
                _entry("2026-07-03T00:00:00", 13),
            ]
        }
        text = render_dashboard_html(histories, _FAKE_PNG, "kw", "US", "2026-07-01", "2026-07-03").decode()

        assert "#10" in text  # best
        assert "#20" in text  # worst
        assert "14.3" in text  # average
        assert "#13" in text  # current rank in the card

    def test_improving_trend_marked_up_worsening_marked_down(self):
        improving = {"App A": [_entry("2026-07-01T00:00:00", 20), _entry("2026-07-02T00:00:00", 10)]}
        worsening = {"App B": [_entry("2026-07-01T00:00:00", 10), _entry("2026-07-02T00:00:00", 20)]}

        improving_html = render_dashboard_html(improving, _FAKE_PNG, "kw", "US", "2026-07-01", "2026-07-02").decode()
        worsening_html = render_dashboard_html(worsening, _FAKE_PNG, "kw", "US", "2026-07-01", "2026-07-02").decode()

        assert 'class="card-trend up"' in improving_html
        assert 'class="card-trend down"' in worsening_html

    def test_app_with_no_data_in_range_shows_empty_state_without_crashing(self):
        histories = {"No Data App": []}
        text = render_dashboard_html(histories, _FAKE_PNG, "kw", "US", "2026-07-01", "2026-07-05").decode()

        assert "No ranking data in this range" in text
        assert "No data" in text  # table row


class TestRenderDashboardHtmlEscaping:
    def test_keyword_is_html_escaped(self):
        html = render_dashboard_html(
            {"App A": [_entry("2026-07-01T00:00:00", 1)]},
            _FAKE_PNG,
            '<script>alert(1)</script>',
            "US",
            "2026-07-01",
            "2026-07-01",
        ).decode()

        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html

    def test_app_label_is_html_escaped(self):
        malicious_label = '<img src=x onerror=alert(1)>'
        html = render_dashboard_html(
            {malicious_label: [_entry("2026-07-01T00:00:00", 1)]},
            _FAKE_PNG,
            "kw",
            "US",
            "2026-07-01",
            "2026-07-01",
        ).decode()

        assert malicious_label not in html
        assert "&lt;img src=x onerror=alert(1)&gt;" in html
