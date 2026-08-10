import pytest

from mcp_task.config import BATCH_LOOKUP_MAX_IDS
from mcp_task.errors import ToolError
from mcp_task.services.appstore import app_service


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


class TestFetchAppsByTrackIds:
    def test_empty_track_ids_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(app_service, "lookup_apps", _no_call)
        with pytest.raises(ToolError, match="cannot be empty"):
            app_service.fetch_apps_by_track_ids("", "us")

    def test_single_id_is_allowed(self, monkeypatch):
        fake_apps = [{"trackId": 1, "trackName": "App One"}]
        monkeypatch.setattr(app_service, "lookup_apps", lambda ids, country: fake_apps)

        requested_ids, apps = app_service.fetch_apps_by_track_ids("1", "us")
        assert requested_ids == [1]
        assert apps == fake_apps

    def test_valid_input_delegates_to_lookup_apps_with_parsed_ids(self, monkeypatch):
        captured = {}
        fake_apps = [{"trackId": 1}, {"trackId": 2}]

        def fake_lookup_apps(ids, country):
            captured["ids"] = ids
            captured["country"] = country
            return fake_apps

        monkeypatch.setattr(app_service, "lookup_apps", fake_lookup_apps)
        requested_ids, apps = app_service.fetch_apps_by_track_ids(" 1 , 2 ", "us")

        assert requested_ids == [1, 2]
        assert captured == {"ids": [1, 2], "country": "us"}
        assert apps == fake_apps

    def test_more_than_batch_lookup_max_ids_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(app_service, "lookup_apps", _no_call)
        ids = ",".join(str(i) for i in range(1, BATCH_LOOKUP_MAX_IDS + 2))
        with pytest.raises(ToolError, match=f"at most {BATCH_LOOKUP_MAX_IDS}"):
            app_service.fetch_apps_by_track_ids(ids, "us")

    def test_invalid_country_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(app_service, "lookup_apps", _no_call)
        with pytest.raises(ToolError):
            app_service.fetch_apps_by_track_ids("1,2", "usa")
