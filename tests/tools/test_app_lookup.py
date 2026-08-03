from mcp_task.clients.itunes import AppLookupError
from mcp_task.tools import app_lookup


class TestGetAppStoreId:
    def test_empty_app_name_returns_validation_error_without_calling_client(self, monkeypatch):
        called = False

        def fail_if_called(*args, **kwargs):
            nonlocal called
            called = True

        monkeypatch.setattr(app_lookup, "search_app", fail_if_called)

        result = app_lookup.get_app_store_id("", "us")
        assert "error" in result
        assert called is False

    def test_success_shapes_app_id_name_and_url(self, monkeypatch):
        fake_app = {"trackId": 529479190, "trackName": "Clash of Clans", "trackViewUrl": "https://example.test/coc"}
        monkeypatch.setattr(app_lookup, "search_app", lambda app_name, country: fake_app)

        result = app_lookup.get_app_store_id("Clash of Clans", "us")
        assert result == {
            "app_id": 529479190,
            "name": "Clash of Clans",
            "url": "https://example.test/coc",
        }

    def test_lookup_failure_returns_error_dict(self, monkeypatch):
        def raise_error(app_name, country):
            raise AppLookupError("No app found for 'nope' in storefront 'us'")

        monkeypatch.setattr(app_lookup, "search_app", raise_error)

        result = app_lookup.get_app_store_id("nope", "us")
        assert result["error"] == "No app found for 'nope' in storefront 'us'"
        assert result["status_code"] is None


class TestGetAppName:
    def test_non_positive_track_id_returns_validation_error_without_calling_client(self, monkeypatch):
        called = False

        def fail_if_called(*args, **kwargs):
            nonlocal called
            called = True

        monkeypatch.setattr(app_lookup, "lookup_app", fail_if_called)

        result = app_lookup.get_app_name(0, "us")
        assert "error" in result
        assert called is False

    def test_success_shapes_app_id_name_and_url(self, monkeypatch):
        fake_app = {"trackId": 570060128, "trackName": "iMovie", "trackViewUrl": "https://example.test/imovie"}
        monkeypatch.setattr(app_lookup, "lookup_app", lambda track_id, country: fake_app)

        result = app_lookup.get_app_name(570060128, "us")
        assert result == {
            "app_id": 570060128,
            "name": "iMovie",
            "url": "https://example.test/imovie",
        }
