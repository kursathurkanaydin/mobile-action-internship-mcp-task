from mcp_task.errors import ToolError
from mcp_task.tools.appstore import keyword_services as ks


class TestGetKeywordRanking:
    def test_success_wraps_service_data_under_rankings(self, monkeypatch):
        monkeypatch.setattr(ks, "fetch_keyword_ranking", lambda *a: [{"keyword": "strategy", "rank": 5}])
        result = ks.get_keyword_ranking(529479190, "US", "strategy")
        assert result == {"rankings": [{"keyword": "strategy", "rank": 5}]}

    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("out of credits", status_code=429)

        monkeypatch.setattr(ks, "fetch_keyword_ranking", raise_error)
        result = ks.get_keyword_ranking(529479190, "US", "strategy")
        assert result == {"error": "out of credits", "status_code": 429}


class TestGetTopKeywords:
    def test_success_wraps_service_data_under_top_keywords(self, monkeypatch):
        fake_data = [{"keyword": "game", "searchVolume": 100, "rank": 3}]
        monkeypatch.setattr(ks, "fetch_top_keywords", lambda *a: fake_data)
        result = ks.get_top_keywords(529479190, "US", "2026-07-01")
        assert result == {"top_keywords": fake_data}

    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("bad input")

        monkeypatch.setattr(ks, "fetch_top_keywords", raise_error)
        result = ks.get_top_keywords(529479190, "US", "2026-07-01", limit=-5)
        assert result == {"error": "bad input", "status_code": None}


class TestGetKeywordRankingHistory:
    def test_success_wraps_service_data_under_history(self, monkeypatch):
        fake_history = [{"date": "2026-07-01T00:00:00", "rank": 10, "appKind": "IPHONE"}]
        monkeypatch.setattr(ks, "fetch_keyword_ranking_history", lambda *a: fake_history)
        result = ks.get_keyword_ranking_history(529479190, "US", "strategy", "2026-07-01", "2026-07-01")
        assert result == {"history": fake_history}

    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("start_date must be on or before end_date")

        monkeypatch.setattr(ks, "fetch_keyword_ranking_history", raise_error)
        result = ks.get_keyword_ranking_history(529479190, "US", "strategy", "2026-07-20", "2026-07-01")
        assert "error" in result


class TestGetKeywordMetadata:
    def test_success_wraps_service_data_under_metadata(self, monkeypatch):
        fake_data = {"searchVolume": 500, "popularity": 80}
        monkeypatch.setattr(ks, "fetch_keyword_metadata", lambda *a: fake_data)
        result = ks.get_keyword_metadata("US", "meditation")
        assert result == {"metadata": fake_data}

    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("'keyword' cannot be empty.")

        monkeypatch.setattr(ks, "fetch_keyword_metadata", raise_error)
        result = ks.get_keyword_metadata("US", "")
        assert "error" in result


class TestGetAppsForKeyword:
    def test_success_wraps_service_data_under_apps(self, monkeypatch):
        fake_data = [{"trackId": 1}, {"trackId": 2}]
        monkeypatch.setattr(ks, "fetch_apps_for_keyword", lambda *a: fake_data)
        result = ks.get_apps_for_keyword("US", "meditation")
        assert result == {"apps": fake_data}

    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("bad country code")

        monkeypatch.setattr(ks, "fetch_apps_for_keyword", raise_error)
        result = ks.get_apps_for_keyword("", "meditation")
        assert "error" in result


class TestGetOrganicKeywords:
    def test_service_error_returns_error_shape(self, monkeypatch):
        def raise_error(*a):
            raise ToolError("bad device")

        monkeypatch.setattr(ks, "fetch_organic_keywords", raise_error)
        result = ks.get_organic_keywords(529479190, "US", "ANDROID", "2026-07-01")
        assert "error" in result

    def test_response_is_sorted_by_rank_and_capped_to_limit(self, monkeypatch):
        rankings = [
            {"keyword": "c", "rank": 30},
            {"keyword": "a", "rank": 5},
            {"keyword": "b", "rank": 15},
        ]
        fake_data = {
            "trackId": 529479190,
            "countryCode": "US",
            "deviceType": "IPHONE",
            "date": "2026-07-01",
            "rankings": rankings,
        }
        monkeypatch.setattr(ks, "fetch_organic_keywords", lambda *a: fake_data)

        result = ks.get_organic_keywords(529479190, "US", "IPHONE", "2026-07-01", limit=2)

        assert result["total_count"] == 3
        assert result["returned_count"] == 2
        assert [item["keyword"] for item in result["rankings"]] == ["a", "b"]

    def test_missing_rank_is_treated_as_worst(self, monkeypatch):
        rankings = [{"keyword": "no-rank"}, {"keyword": "ranked", "rank": 1}]
        fake_data = {"rankings": rankings}
        monkeypatch.setattr(ks, "fetch_organic_keywords", lambda *a: fake_data)

        result = ks.get_organic_keywords(529479190, "US", "IPHONE", "2026-07-01", limit=2)

        assert [item["keyword"] for item in result["rankings"]] == ["ranked", "no-rank"]
