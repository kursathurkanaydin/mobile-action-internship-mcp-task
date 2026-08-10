from mcp_task.errors import ToolError
from mcp_task.tools.compare import keyword_services as ks


class TestCompareStoresKeywordMetadata:
    def test_success_wraps_each_side_under_metadata(self, monkeypatch):
        fake_data = {"app_store": {"searchVolume": 51}, "play_store": {"searchVolume": 51}}
        monkeypatch.setattr(ks, "fetch_keyword_metadata", lambda *a: fake_data)

        result = ks.compare_stores_keyword_metadata("US", "strategy")
        assert result == {
            "app_store": {"metadata": {"searchVolume": 51}},
            "play_store": {"metadata": {"searchVolume": 51}},
        }

    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("bad country code", error_type="validation")

        monkeypatch.setattr(ks, "fetch_keyword_metadata", raise_error)
        result = ks.compare_stores_keyword_metadata("usa", "strategy")
        assert "error" in result


class TestCompareStoresKeywordRanking:
    def test_success_wraps_each_side_under_rankings(self, monkeypatch):
        fake_data = {"app_store": [{"rank": 1}], "play_store": [{"rank": 2}]}
        monkeypatch.setattr(ks, "fetch_keyword_ranking", lambda *a: fake_data)

        result = ks.compare_stores_keyword_ranking(529479190, "com.supercell.clashofclans", "US", "clan")
        assert result == {"app_store": {"rankings": [{"rank": 1}]}, "play_store": {"rankings": [{"rank": 2}]}}

    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("not a valid App Store track id", error_type="validation")

        monkeypatch.setattr(ks, "fetch_keyword_ranking", raise_error)
        result = ks.compare_stores_keyword_ranking(-1, "com.supercell.clashofclans", "US", "clan")
        assert "error" in result


class TestCompareStoresKeywordRankingHistory:
    def test_success_wraps_each_side_under_history(self, monkeypatch):
        fake_data = {"app_store": [{"date": "2026-07-01", "rank": 1}], "play_store": [{"date": "2026-07-01", "rank": 2}]}
        monkeypatch.setattr(ks, "fetch_keyword_ranking_history", lambda *a: fake_data)

        result = ks.compare_stores_keyword_ranking_history(
            529479190, "com.supercell.clashofclans", "US", "clan", "2026-07-01", "2026-07-10"
        )
        assert result == {
            "app_store": {"history": [{"date": "2026-07-01", "rank": 1}]},
            "play_store": {"history": [{"date": "2026-07-01", "rank": 2}]},
        }

    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("start_date must be on or before end_date", error_type="validation")

        monkeypatch.setattr(ks, "fetch_keyword_ranking_history", raise_error)
        result = ks.compare_stores_keyword_ranking_history(
            529479190, "com.supercell.clashofclans", "US", "clan", "2026-07-20", "2026-07-01"
        )
        assert "error" in result


class TestCompareStoresTopKeywords:
    def test_success_wraps_each_side_under_top_keywords(self, monkeypatch):
        fake_data = {"app_store": [{"keyword": "clan"}], "play_store": [{"keyword": "war"}]}
        monkeypatch.setattr(ks, "fetch_top_keywords", lambda *a: fake_data)

        result = ks.compare_stores_top_keywords(529479190, "com.supercell.clashofclans", "US", "2026-07-01")
        assert result == {
            "app_store": {"top_keywords": [{"keyword": "clan"}]},
            "play_store": {"top_keywords": [{"keyword": "war"}]},
        }

    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("bad input", error_type="validation")

        monkeypatch.setattr(ks, "fetch_top_keywords", raise_error)
        result = ks.compare_stores_top_keywords(529479190, "com.supercell.clashofclans", "US", "2026-07-01")
        assert "error" in result
