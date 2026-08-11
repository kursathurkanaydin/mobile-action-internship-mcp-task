import pytest
from fastmcp.exceptions import ToolError as FastMCPToolError

from mcp_task.tools.compare import charts

_APP_STORE_RANKINGS = [
    {"keyword": "clan", "rank": 1, "appKind": "IPHONE"},
    {"keyword": "clan", "rank": 3, "appKind": "IPAD"},
    {"keyword": "war", "rank": 59, "appKind": "IPHONE"},
]
_PLAY_STORE_RANKINGS = [
    {"keyword": "clan", "rank": 2},
]

_APP_STORE_HISTORY = [
    {"date": "2026-07-01T00:00:00", "rank": 20, "appKind": "IPHONE"},
    {"date": "2026-07-01T00:00:00", "rank": 25, "appKind": "IPAD"},
    {"date": "2026-07-02T00:00:00", "rank": 15, "appKind": "IPHONE"},
]
_PLAY_STORE_HISTORY = [
    {"date": "2026-07-01T00:00:00", "rank": 10},
    {"date": "2026-07-02T00:00:00", "rank": 8},
]


class TestRankByKeyword:
    def test_picks_best_rank_across_devices(self):
        result = charts._rank_by_keyword(_APP_STORE_RANKINGS, ["clan", "war"])
        assert result == {"clan": 1, "war": 59}

    def test_missing_keyword_maps_to_none(self):
        result = charts._rank_by_keyword(_PLAY_STORE_RANKINGS, ["clan", "war"])
        assert result == {"clan": 2, "war": None}

    def test_empty_rankings_returns_all_none(self):
        assert charts._rank_by_keyword([], ["clan", "war"]) == {"clan": None, "war": None}


class TestPlotCompareStoresKeywordRanking:
    def test_invalid_input_raises_fastmcp_tool_error(self):
        with pytest.raises(FastMCPToolError):
            charts.plot_compare_stores_keyword_ranking(-1, "com.supercell.clashofclans", "US", "clan")

    def test_no_data_on_either_store_raises_fastmcp_tool_error(self, monkeypatch):
        monkeypatch.setattr(
            charts, "fetch_keyword_ranking", lambda *a: {"app_store": [], "play_store": []}
        )
        with pytest.raises(FastMCPToolError, match="No ranking data found"):
            charts.plot_compare_stores_keyword_ranking(529479190, "com.supercell.clashofclans", "US", "clan")

    def test_success_returns_chart_url_from_publish_html(self, monkeypatch):
        monkeypatch.setattr(
            charts,
            "fetch_keyword_ranking",
            lambda *a: {"app_store": _APP_STORE_RANKINGS, "play_store": _PLAY_STORE_RANKINGS},
        )
        monkeypatch.setattr(charts, "_resolve_app_label", lambda *a: "Clash of Clans")
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        result = charts.plot_compare_stores_keyword_ranking(
            529479190, "com.supercell.clashofclans", "US", "clan,war"
        )
        assert result == {"chart_url": "http://127.0.0.1:9/fake.html"}

    def test_dashboard_built_with_best_rank_per_keyword_per_store(self, monkeypatch):
        captured = {}

        def fake_render(app_name, app_store_ranks, play_store_ranks, keywords, country_code, date):
            captured["app_name"] = app_name
            captured["app_store_ranks"] = app_store_ranks
            captured["play_store_ranks"] = play_store_ranks
            captured["keywords"] = keywords
            return b"<html></html>"

        monkeypatch.setattr(
            charts,
            "fetch_keyword_ranking",
            lambda *a: {"app_store": _APP_STORE_RANKINGS, "play_store": _PLAY_STORE_RANKINGS},
        )
        monkeypatch.setattr(charts, "_resolve_app_label", lambda *a: "Clash of Clans")
        monkeypatch.setattr(charts, "render_ranking_comparison_dashboard", fake_render)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.plot_compare_stores_keyword_ranking(529479190, "com.supercell.clashofclans", "US", " clan , war ")

        assert captured["app_name"] == "Clash of Clans"
        assert captured["keywords"] == ["clan", "war"]
        assert captured["app_store_ranks"] == {"clan": 1, "war": 59}
        assert captured["play_store_ranks"] == {"clan": 2, "war": None}


class TestPlotCompareStoresKeywordRankingHistory:
    def test_invalid_input_raises_fastmcp_tool_error(self):
        with pytest.raises(FastMCPToolError):
            charts.plot_compare_stores_keyword_ranking_history(
                -1, "com.supercell.clashofclans", "US", "clan", "2026-07-01", "2026-07-05"
            )

    def test_no_history_on_either_store_raises_fastmcp_tool_error(self, monkeypatch):
        monkeypatch.setattr(
            charts, "fetch_keyword_ranking_history", lambda *a: {"app_store": [], "play_store": []}
        )
        with pytest.raises(FastMCPToolError, match="No ranking history found"):
            charts.plot_compare_stores_keyword_ranking_history(
                529479190, "com.supercell.clashofclans", "US", "clan", "2026-07-01", "2026-07-05"
            )

    def test_success_returns_chart_url_from_publish_html(self, monkeypatch):
        monkeypatch.setattr(
            charts,
            "fetch_keyword_ranking_history",
            lambda *a: {"app_store": _APP_STORE_HISTORY, "play_store": _PLAY_STORE_HISTORY},
        )
        monkeypatch.setattr(charts, "_resolve_app_label", lambda *a: "Clash of Clans")
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        result = charts.plot_compare_stores_keyword_ranking_history(
            529479190, "com.supercell.clashofclans", "US", "clan", "2026-07-01", "2026-07-02"
        )
        assert result == {"chart_url": "http://127.0.0.1:9/fake.html"}

    def test_dashboard_built_with_one_series_per_store_using_compare_platform(self, monkeypatch):
        captured = {}

        def fake_render(histories_by_app, keyword, country_code, start_date, end_date, platform, series_label):
            captured["histories_by_app"] = histories_by_app
            captured["keyword"] = keyword
            captured["platform"] = platform
            captured["series_label"] = series_label
            return b"<html></html>"

        monkeypatch.setattr(
            charts,
            "fetch_keyword_ranking_history",
            lambda *a: {"app_store": _APP_STORE_HISTORY, "play_store": _PLAY_STORE_HISTORY},
        )
        monkeypatch.setattr(charts, "_resolve_app_label", lambda *a: "Clash of Clans")
        monkeypatch.setattr(charts, "render_dashboard_html", fake_render)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.plot_compare_stores_keyword_ranking_history(
            529479190, "com.supercell.clashofclans", "US", "clan", "2026-07-01", "2026-07-02"
        )

        assert captured["histories_by_app"] == {"App Store": _APP_STORE_HISTORY, "Play Store": _PLAY_STORE_HISTORY}
        assert captured["keyword"] == "Clash of Clans: clan"
        assert captured["platform"] is charts.COMPARE
        assert captured["series_label"] == "Store"

    def test_one_store_having_data_is_enough_not_to_fail(self, monkeypatch):
        # matches the App Store's own compare_appstore_keyword_ranking_history precedent:
        # tolerate one side being empty, only fail if BOTH sides are empty
        monkeypatch.setattr(
            charts, "fetch_keyword_ranking_history", lambda *a: {"app_store": _APP_STORE_HISTORY, "play_store": []}
        )
        monkeypatch.setattr(charts, "_resolve_app_label", lambda *a: "Clash of Clans")
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        result = charts.plot_compare_stores_keyword_ranking_history(
            529479190, "com.supercell.clashofclans", "US", "clan", "2026-07-01", "2026-07-02"
        )
        assert result == {"chart_url": "http://127.0.0.1:9/fake.html"}
