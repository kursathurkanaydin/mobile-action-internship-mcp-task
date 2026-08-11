import pytest
from fastmcp.exceptions import ToolError as FastMCPToolError

from mcp_task.clients.mobileaction import MobileActionAPIError
from mcp_task.tools.playstore import charts

_HISTORY = [
    {"date": "2026-07-01T00:00:00", "rank": 20},
    {"date": "2026-07-02T00:00:00", "rank": 15},
]


class TestResolveAppLabel:
    def test_returns_app_name_on_success(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_app_by_track_id", lambda track_id, lang_code: {"name": "Clash of Clans"})
        assert charts._resolve_app_label("com.supercell.clashofclans") == "Clash of Clans"

    def test_falls_back_to_track_id_on_lookup_failure(self, monkeypatch):
        def raise_error(track_id, lang_code):
            raise MobileActionAPIError("not found", status_code=404)

        monkeypatch.setattr(charts, "fetch_app_by_track_id", raise_error)
        assert charts._resolve_app_label("com.supercell.clashofclans") == "com.supercell.clashofclans"

    def test_falls_back_to_track_id_when_name_missing(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_app_by_track_id", lambda track_id, lang_code: {})
        assert charts._resolve_app_label("com.supercell.clashofclans") == "com.supercell.clashofclans"


class TestPlotPlaystoreKeywordRankingHistory:
    def test_invalid_input_raises_fastmcp_tool_error(self):
        with pytest.raises(FastMCPToolError):
            charts.plot_playstore_keyword_ranking_history(
                "not-a-package-name", "US", "game", "2026-07-01", "2026-07-05"
            )

    def test_no_history_found_raises_fastmcp_tool_error(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_keyword_ranking_history", lambda *a: [])

        with pytest.raises(FastMCPToolError, match="No ranking history found"):
            charts.plot_playstore_keyword_ranking_history(
                "com.supercell.clashofclans", "US", "game", "2026-07-01", "2026-07-05"
            )

    def test_success_returns_chart_url_from_publish_html(self, monkeypatch):
        monkeypatch.setattr(charts, "fetch_keyword_ranking_history", lambda *a: _HISTORY)
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id: "Clash of Clans")
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        result = charts.plot_playstore_keyword_ranking_history(
            "com.supercell.clashofclans", "US", "game", "2026-07-01", "2026-07-02"
        )
        assert result == {"chart_url": "http://127.0.0.1:9/fake.html"}

    def test_dashboard_is_built_for_a_single_app_using_play_store_platform(self, monkeypatch):
        captured = {}

        def fake_render(histories_by_app, keyword, country_code, start_date, end_date, platform):
            captured["histories_by_app"] = histories_by_app
            captured["keyword"] = keyword
            captured["platform"] = platform
            return b"<html></html>"

        monkeypatch.setattr(charts, "fetch_keyword_ranking_history", lambda *a: _HISTORY)
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id: "Clash of Clans")
        monkeypatch.setattr(charts, "render_dashboard_html", fake_render)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.plot_playstore_keyword_ranking_history(
            "com.supercell.clashofclans", "US", "game", "2026-07-01", "2026-07-02"
        )

        assert captured["histories_by_app"] == {"Clash of Clans": _HISTORY}
        assert captured["keyword"] == "game"
        assert captured["platform"] is charts.PLAY_STORE


class TestPlotPlaystoreKeywordRankingHistoryMulti:
    def test_invalid_input_raises_fastmcp_tool_error(self):
        with pytest.raises(FastMCPToolError):
            charts.plot_playstore_keyword_ranking_history_multi(
                "not-a-package-name", "US", "game,strategy", "2026-07-01", "2026-07-05"
            )

    def test_no_history_for_any_keyword_raises_fastmcp_tool_error(self, monkeypatch):
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id: "Clash of Clans")
        monkeypatch.setattr(charts, "fetch_keyword_ranking_history_multi", lambda *a: {"game": [], "clan": []})

        with pytest.raises(FastMCPToolError, match="No ranking history found"):
            charts.plot_playstore_keyword_ranking_history_multi(
                "com.supercell.clashofclans", "US", "game,clan", "2026-07-01", "2026-07-05"
            )

    def test_success_returns_chart_url_from_publish_html(self, monkeypatch):
        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id: "Clash of Clans")
        monkeypatch.setattr(
            charts, "fetch_keyword_ranking_history_multi", lambda *a: {"game": _HISTORY, "clan": _HISTORY}
        )
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        result = charts.plot_playstore_keyword_ranking_history_multi(
            "com.supercell.clashofclans", "US", "game,clan", "2026-07-01", "2026-07-02"
        )
        assert result == {"chart_url": "http://127.0.0.1:9/fake.html"}

    def test_dashboard_is_built_with_one_series_per_keyword_using_play_store_platform(self, monkeypatch):
        captured = {}

        def fake_render(histories_by_app, keyword, country_code, start_date, end_date, platform, series_label):
            captured["histories_by_app"] = histories_by_app
            captured["keyword"] = keyword
            captured["platform"] = platform
            captured["series_label"] = series_label
            return b"<html></html>"

        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id: "Clash of Clans")
        monkeypatch.setattr(
            charts, "fetch_keyword_ranking_history_multi", lambda *a: {"game": _HISTORY, "clan": _HISTORY}
        )
        monkeypatch.setattr(charts, "render_dashboard_html", fake_render)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.plot_playstore_keyword_ranking_history_multi(
            "com.supercell.clashofclans", "US", "game,clan", "2026-07-01", "2026-07-02"
        )

        assert captured["histories_by_app"] == {"game": _HISTORY, "clan": _HISTORY}
        assert captured["keyword"] == "Clash of Clans"
        assert captured["platform"] is charts.PLAY_STORE
        assert captured["series_label"] == "Keyword"

    def test_fetches_once_for_all_keywords_not_once_per_keyword(self, monkeypatch):
        calls = []

        def fake_fetch(track_id, country_code, keywords, start_date, end_date):
            calls.append(keywords)
            return {"game": _HISTORY, "clan": _HISTORY}

        monkeypatch.setattr(charts, "_resolve_app_label", lambda track_id: "Clash of Clans")
        monkeypatch.setattr(charts, "fetch_keyword_ranking_history_multi", fake_fetch)
        monkeypatch.setattr(charts, "publish_html", lambda html_bytes: "http://127.0.0.1:9/fake.html")

        charts.plot_playstore_keyword_ranking_history_multi(
            "com.supercell.clashofclans", "US", "game,clan", "2026-07-01", "2026-07-02"
        )
        assert calls == ["game,clan"]
