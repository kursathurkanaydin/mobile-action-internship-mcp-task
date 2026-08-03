import pytest

from mcp_task.errors import ToolError
from mcp_task.services import keyword_service as ks


def _no_call(*args, **kwargs):
    raise AssertionError("the MobileAction client should not be called for invalid input")


class TestFetchKeywordRanking:
    def test_invalid_track_id_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        with pytest.raises(ToolError):
            ks.fetch_keyword_ranking(0, "US", "strategy", None)

    def test_valid_input_calls_client_with_expected_path_and_params(self, monkeypatch):
        captured = {}

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return [{"keyword": "strategy", "rank": 5}]

        monkeypatch.setattr(ks, "get", fake_get)
        result = ks.fetch_keyword_ranking(529479190, "us", "strategy", None)

        assert captured["path"] == "/appstore-keyword-ranking/529479190/US/keywordrankings"
        assert captured["params"] == {"keywords": "strategy", "date": None}
        assert result == [{"keyword": "strategy", "rank": 5}]

    def test_optional_date_is_validated_when_provided(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        with pytest.raises(ToolError, match="date"):
            ks.fetch_keyword_ranking(529479190, "US", "strategy", "not-a-date")


class TestFetchTopKeywords:
    def test_invalid_limit_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        with pytest.raises(ToolError):
            ks.fetch_top_keywords(529479190, "US", "2026-07-01", None, -5)

    def test_valid_input_calls_client_with_expected_path_and_params(self, monkeypatch):
        captured = {}

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return [{"keyword": "game", "searchVolume": 100, "rank": 3}]

        monkeypatch.setattr(ks, "get", fake_get)
        result = ks.fetch_top_keywords(529479190, "US", "2026-07-01", "iphone", 50)

        assert captured["path"] == "/appstore-keyword-ranking/529479190/US/top-keywords"
        assert captured["params"] == {"date": "2026-07-01", "device": "IPHONE", "limit": 50}
        assert result == [{"keyword": "game", "searchVolume": 100, "rank": 3}]


class TestFetchKeywordRankingHistory:
    def test_invalid_date_range_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        with pytest.raises(ToolError, match="before"):
            ks.fetch_keyword_ranking_history(529479190, "US", "strategy", "2026-07-20", "2026-07-01")

    def test_valid_input_calls_client_with_expected_path_and_params(self, monkeypatch):
        captured = {}
        fake_history = [{"date": "2026-07-01T00:00:00", "rank": 10, "appKind": "IPHONE"}]

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_history

        monkeypatch.setattr(ks, "get", fake_get)
        result = ks.fetch_keyword_ranking_history(529479190, "US", "strategy", "2026-07-01", "2026-07-01")

        assert captured["path"] == "/appstore-keyword-ranking/529479190/US/strategy/keywordrankings"
        assert captured["params"] == {"startDate": "2026-07-01", "endDate": "2026-07-01"}
        assert result == fake_history


class TestFetchKeywordMetadata:
    def test_empty_keyword_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        with pytest.raises(ToolError, match="cannot be empty"):
            ks.fetch_keyword_metadata("US", "")

    def test_valid_input_calls_client_with_expected_path_and_params(self, monkeypatch):
        captured = {}
        fake_data = {"searchVolume": 500, "popularity": 80}

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_data

        monkeypatch.setattr(ks, "get", fake_get)
        result = ks.fetch_keyword_metadata("US", "meditation")

        assert captured["path"] == "/appstore-keyword-ranking/US/keyword-metadata"
        assert captured["params"] == {"keyword": "meditation"}
        assert result == fake_data


class TestFetchAppsForKeyword:
    def test_invalid_country_code_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        with pytest.raises(ToolError):
            ks.fetch_apps_for_keyword("", "meditation")

    def test_valid_input_calls_client_with_expected_path_and_params(self, monkeypatch):
        captured = {}
        fake_data = [{"trackId": 1}, {"trackId": 2}]

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_data

        monkeypatch.setattr(ks, "get", fake_get)
        result = ks.fetch_apps_for_keyword("US", "meditation")

        assert captured["path"] == "/appstore-keyword-ranking/US/keyword-apps"
        assert captured["params"] == {"keyword": "meditation"}
        assert result == fake_data


class TestFetchOrganicKeywords:
    def test_invalid_device_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        with pytest.raises(ToolError):
            ks.fetch_organic_keywords(529479190, "US", "ANDROID", "2026-07-01", 100)

    def test_valid_input_calls_client_with_expected_path_and_params(self, monkeypatch):
        captured = {}
        fake_data = {"rankings": []}

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_data

        monkeypatch.setattr(ks, "get", fake_get)
        result = ks.fetch_organic_keywords(529479190, "US", "iphone", "2026-07-01", 100)

        assert captured["path"] == "/appstore-keyword-ranking/529479190/US/IPHONE/organic-keywords"
        assert captured["params"] == {"date": "2026-07-01"}
        assert result == fake_data
