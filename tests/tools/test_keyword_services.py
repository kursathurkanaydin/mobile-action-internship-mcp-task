from mcp_task.clients.mobileaction import MobileActionAPIError
from mcp_task.tools import keyword_services as ks


def _no_call(*args, **kwargs):
    raise AssertionError("the MobileAction client should not be called for invalid input")


class TestGetKeywordRanking:
    def test_invalid_track_id_short_circuits_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        result = ks.get_keyword_ranking(0, "US", "strategy")
        assert "error" in result

    def test_success_wraps_client_data_under_rankings(self, monkeypatch):
        monkeypatch.setattr(ks, "get", lambda path, params: [{"keyword": "strategy", "rank": 5}])
        result = ks.get_keyword_ranking(529479190, "us", "strategy")
        assert result == {"rankings": [{"keyword": "strategy", "rank": 5}]}

    def test_api_failure_returns_error_shape(self, monkeypatch):
        def raise_error(path, params):
            raise MobileActionAPIError("out of credits", status_code=429)

        monkeypatch.setattr(ks, "get", raise_error)
        result = ks.get_keyword_ranking(529479190, "US", "strategy")
        assert result == {"error": "out of credits", "status_code": 429}


class TestGetTopKeywords:
    def test_invalid_limit_short_circuits_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        result = ks.get_top_keywords(529479190, "US", "2026-07-01", limit=-5)
        assert "error" in result

    def test_success_wraps_client_data_under_top_keywords(self, monkeypatch):
        fake_data = [{"keyword": "game", "searchVolume": 100, "rank": 3}]
        monkeypatch.setattr(ks, "get", lambda path, params: fake_data)
        result = ks.get_top_keywords(529479190, "US", "2026-07-01")
        assert result == {"top_keywords": fake_data}


class TestFetchKeywordRankingHistory:
    def test_invalid_date_range_raises(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        import pytest

        from mcp_task.errors import ToolError

        with pytest.raises(ToolError):
            ks.fetch_keyword_ranking_history(529479190, "US", "strategy", "2026-07-20", "2026-07-01")

    def test_success_returns_raw_client_data(self, monkeypatch):
        fake_history = [{"date": "2026-07-01T00:00:00", "rank": 10, "appKind": "IPHONE"}]
        monkeypatch.setattr(ks, "get", lambda path, params: fake_history)
        result = ks.fetch_keyword_ranking_history(529479190, "US", "strategy", "2026-07-01", "2026-07-01")
        assert result == fake_history


class TestGetKeywordRankingHistory:
    def test_invalid_country_code_returns_error_dict(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        result = ks.get_keyword_ranking_history(529479190, "USA", "strategy", "2026-07-01", "2026-07-05")
        assert "error" in result

    def test_success_wraps_client_data_under_history(self, monkeypatch):
        fake_history = [{"date": "2026-07-01T00:00:00", "rank": 10, "appKind": "IPHONE"}]
        monkeypatch.setattr(ks, "get", lambda path, params: fake_history)
        result = ks.get_keyword_ranking_history(529479190, "US", "strategy", "2026-07-01", "2026-07-01")
        assert result == {"history": fake_history}


class TestGetKeywordMetadata:
    def test_empty_keyword_returns_error_dict(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        result = ks.get_keyword_metadata("US", "")
        assert "error" in result

    def test_success_wraps_client_data_under_metadata(self, monkeypatch):
        fake_data = {"searchVolume": 500, "popularity": 80}
        monkeypatch.setattr(ks, "get", lambda path, params: fake_data)
        result = ks.get_keyword_metadata("US", "meditation")
        assert result == {"metadata": fake_data}


class TestGetAppsForKeyword:
    def test_invalid_country_code_returns_error_dict(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        result = ks.get_apps_for_keyword("", "meditation")
        assert "error" in result

    def test_success_wraps_client_data_under_apps(self, monkeypatch):
        fake_data = [{"trackId": 1}, {"trackId": 2}]
        monkeypatch.setattr(ks, "get", lambda path, params: fake_data)
        result = ks.get_apps_for_keyword("US", "meditation")
        assert result == {"apps": fake_data}


class TestGetOrganicKeywords:
    def test_invalid_device_returns_error_dict(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
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
        monkeypatch.setattr(ks, "get", lambda path, params: fake_data)

        result = ks.get_organic_keywords(529479190, "US", "IPHONE", "2026-07-01", limit=2)

        assert result["total_count"] == 3
        assert result["returned_count"] == 2
        assert [item["keyword"] for item in result["rankings"]] == ["a", "b"]

    def test_missing_rank_is_treated_as_worst(self, monkeypatch):
        rankings = [{"keyword": "no-rank"}, {"keyword": "ranked", "rank": 1}]
        fake_data = {"rankings": rankings}
        monkeypatch.setattr(ks, "get", lambda path, params: fake_data)

        result = ks.get_organic_keywords(529479190, "US", "IPHONE", "2026-07-01", limit=2)

        assert [item["keyword"] for item in result["rankings"]] == ["ranked", "no-rank"]
