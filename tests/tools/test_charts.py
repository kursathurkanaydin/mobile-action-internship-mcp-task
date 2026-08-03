import pytest
from fastmcp.exceptions import ToolError as FastMCPToolError

from mcp_task.clients.itunes import AppLookupError
from mcp_task.tools import charts

_HISTORY = [
    {"date": "2026-07-01T00:00:00", "rank": 20, "appKind": "IPHONE"},
    {"date": "2026-07-02T00:00:00", "rank": 15, "appKind": "IPHONE"},
]

_RANKINGS = [
    {"keyword": "clan", "rank": 1, "date": "2026-08-02T00:45:18", "appKind": "IPHONE"},
    {"keyword": "war", "rank": 59, "date": "2026-08-02T00:45:17", "appKind": "IPHONE"},
]


class TestPlotKeywordRanking:
    def test_invalid_input_raises_fastmcp_tool_error(self):
        with pytest.raises(FastMCPToolError):
            charts.plot_keyword_ranking(-1, "US", "clan,war")

    def test_no_rankings_found_raises_fastmcp_tool_error(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_keyword_ranking", lambda *a: [])

        with pytest.raises(FastMCPToolError, match="No ranking data found"):
            charts.plot_keyword_ranking(529479190, "US", "clan,war")

    def test_success_returns_chart_url_from_publish_html(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_keyword_ranking", lambda *a: _RANKINGS)
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id, country: "Clash of Clans")
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        result = charts.plot_keyword_ranking(529479190, "US", "clan,war")
        assert result == {"chart_url": "http://127.0.0.1:9/fake.html"}

    def test_dashboard_is_built_with_the_parsed_keyword_list(self, monkeypatch):
        captured = {}

        def fake_render(rankings, keywords, app_name, country_code, snapshot_date):
            captured["keywords"] = keywords
            return b"<html></html>"

        monkeypatch.setattr(charts, "fetch_keyword_ranking", lambda *a: _RANKINGS)
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id, country: "Clash of Clans")
        monkeypatch.setattr(charts, "render_keyword_ranking_dashboard", fake_render)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.plot_keyword_ranking(529479190, "US", " clan , war ")
        assert captured["keywords"] == ["clan", "war"]

    def test_snapshot_date_defaults_to_first_ranking_entrys_date_when_not_given(self, monkeypatch):
        captured = {}

        def fake_render(rankings, keywords, app_name, country_code, snapshot_date):
            captured["snapshot_date"] = snapshot_date
            return b"<html></html>"

        monkeypatch.setattr(charts, "fetch_keyword_ranking", lambda *a: _RANKINGS)
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id, country: "Clash of Clans")
        monkeypatch.setattr(charts, "render_keyword_ranking_dashboard", fake_render)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.plot_keyword_ranking(529479190, "US", "clan,war")
        assert captured["snapshot_date"] == "2026-08-02"

    def test_snapshot_date_uses_the_requested_date_when_given(self, monkeypatch):
        captured = {}

        def fake_render(rankings, keywords, app_name, country_code, snapshot_date):
            captured["snapshot_date"] = snapshot_date
            return b"<html></html>"

        monkeypatch.setattr(charts, "fetch_keyword_ranking", lambda *a: _RANKINGS)
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id, country: "Clash of Clans")
        monkeypatch.setattr(charts, "render_keyword_ranking_dashboard", fake_render)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.plot_keyword_ranking(529479190, "US", "clan,war", "2026-07-15")
        assert captured["snapshot_date"] == "2026-07-15"


class TestPlotKeywordRankingHistory:
    def test_invalid_input_raises_fastmcp_tool_error(self):
        with pytest.raises(FastMCPToolError):
            charts.plot_keyword_ranking_history(-1, "US", "strategy", "2026-07-01", "2026-07-05")

    def test_no_history_found_raises_fastmcp_tool_error(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_keyword_ranking_history", lambda *a: [])

        with pytest.raises(FastMCPToolError, match="No ranking history found"):
            charts.plot_keyword_ranking_history(529479190, "US", "strategy", "2026-07-01", "2026-07-05")

    def test_success_returns_chart_url_from_publish_html(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_keyword_ranking_history", lambda *a: _HISTORY)
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id, country: f"App {track_id}")
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        result = charts.plot_keyword_ranking_history(529479190, "US", "strategy", "2026-07-01", "2026-07-02")
        assert result == {"chart_url": "http://127.0.0.1:9/fake.html"}

    def test_dashboard_is_built_for_a_single_app(self, monkeypatch):
        captured = {}

        def fake_render(histories_by_app, keyword, country_code, start_date, end_date):
            captured["histories_by_app"] = histories_by_app
            return b"<html></html>"

        monkeypatch.setattr(charts, "fetch_keyword_ranking_history", lambda *a: _HISTORY)
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id, country: "Clash of Clans")
        monkeypatch.setattr(charts, "render_dashboard_html", fake_render)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.plot_keyword_ranking_history(529479190, "US", "strategy", "2026-07-01", "2026-07-02")
        assert captured["histories_by_app"] == {"Clash of Clans": _HISTORY}


class TestResolveAppLabel:
    def test_returns_app_name_on_success(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_app_by_track_id", lambda track_id, country: {"trackName": "Clash of Clans"})
        assert charts._resolve_app_label(529479190, "US") == "Clash of Clans"

    def test_falls_back_to_track_id_on_lookup_failure(self, monkeypatch):
        def raise_error(track_id, country):
            raise AppLookupError("no app found")

        monkeypatch.setattr(charts, "fetch_app_by_track_id", raise_error)
        assert charts._resolve_app_label(529479190, "US") == "App 529479190"

    def test_falls_back_to_track_id_when_name_missing(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_app_by_track_id", lambda track_id, country: {})
        assert charts._resolve_app_label(529479190, "US") == "App 529479190"


class TestCompareKeywordRankingHistory:
    def test_invalid_track_ids_raises_fastmcp_tool_error(self):
        with pytest.raises(FastMCPToolError):
            charts.compare_keyword_ranking_history("111", "US", "strategy", "2026-07-01", "2026-07-05")

    def test_no_history_for_any_app_raises_fastmcp_tool_error(self, monkeypatch):
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id, country: f"App {track_id}")
        monkeypatch.setattr(charts, "fetch_keyword_ranking_history", lambda *a: [])

        with pytest.raises(FastMCPToolError, match="No ranking history found"):
            charts.compare_keyword_ranking_history("111,222", "US", "strategy", "2026-07-01", "2026-07-05")

    def test_success_returns_dashboard_url_from_publish_html(self, monkeypatch):
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id, country: f"App {track_id}")
        monkeypatch.setattr(charts, "fetch_keyword_ranking_history", lambda *a: _HISTORY)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        result = charts.compare_keyword_ranking_history("111,222", "US", "strategy", "2026-07-01", "2026-07-02")
        assert result == {"dashboard_url": "http://127.0.0.1:9/fake.html"}

    def test_fetches_history_once_per_distinct_app(self, monkeypatch):
        calls = []

        def fake_fetch(track_id, country_code, keyword, start_date, end_date):
            calls.append(track_id)
            return _HISTORY

        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id, country: f"App {track_id}")
        monkeypatch.setattr(charts, "fetch_keyword_ranking_history", fake_fetch)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.compare_keyword_ranking_history("111,222,333", "US", "strategy", "2026-07-01", "2026-07-02")
        assert calls == [111, 222, 333]
