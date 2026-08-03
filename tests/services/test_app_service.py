import pytest

from mcp_task.errors import ToolError
from mcp_task.services import app_service


def _no_call(*args, **kwargs):
    raise AssertionError("the iTunes client should not be called for invalid input")


class TestFetchAppByName:
    def test_empty_app_name_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(app_service, "search_app", _no_call)
        with pytest.raises(ToolError, match="cannot be empty"):
            app_service.fetch_app_by_name("", "us")

    def test_valid_input_delegates_to_search_app_with_expected_args(self, monkeypatch):
        captured = {}
        fake_app = {"trackId": 529479190, "trackName": "Clash of Clans"}

        def fake_search(app_name, country):
            captured["app_name"] = app_name
            captured["country"] = country
            return fake_app

        monkeypatch.setattr(app_service, "search_app", fake_search)
        result = app_service.fetch_app_by_name("  Clash of Clans  ", "us")

        assert captured == {"app_name": "Clash of Clans", "country": "us"}
        assert result == fake_app

    def test_invalid_country_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(app_service, "search_app", _no_call)
        with pytest.raises(ToolError):
            app_service.fetch_app_by_name("Clash of Clans", "usa")


class TestFetchAppByTrackId:
    def test_non_positive_track_id_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(app_service, "lookup_app", _no_call)
        with pytest.raises(ToolError):
            app_service.fetch_app_by_track_id(0, "us")

    def test_valid_input_delegates_to_lookup_app_with_expected_args(self, monkeypatch):
        captured = {}
        fake_app = {"trackId": 570060128, "trackName": "iMovie"}

        def fake_lookup(track_id, country):
            captured["track_id"] = track_id
            captured["country"] = country
            return fake_app

        monkeypatch.setattr(app_service, "lookup_app", fake_lookup)
        result = app_service.fetch_app_by_track_id(570060128, "us")

        assert captured == {"track_id": 570060128, "country": "us"}
        assert result == fake_app
