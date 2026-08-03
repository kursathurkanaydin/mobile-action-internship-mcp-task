from mcp_task.errors import ToolError
from mcp_task.tools import app_lookup


class TestGetAppStoreId:
    def test_success_shapes_app_id_name_and_url(self, monkeypatch):
        fake_app = {"trackId": 529479190, "trackName": "Clash of Clans", "trackViewUrl": "https://example.test/coc"}
        monkeypatch.setattr(app_lookup, "fetch_app_by_name", lambda app_name, country: fake_app)

        result = app_lookup.get_app_store_id("Clash of Clans", "us")
        assert result == {
            "app_id": 529479190,
            "name": "Clash of Clans",
            "url": "https://example.test/coc",
        }

    def test_service_error_returns_error_dict(self, monkeypatch):
        def raise_error(app_name, country):
            raise ToolError("No app found for 'nope' in storefront 'us'")

        monkeypatch.setattr(app_lookup, "fetch_app_by_name", raise_error)

        result = app_lookup.get_app_store_id("nope", "us")
        assert result["error"] == "No app found for 'nope' in storefront 'us'"
        assert result["status_code"] is None


class TestGetAppName:
    def test_success_shapes_app_id_name_and_url(self, monkeypatch):
        fake_app = {"trackId": 570060128, "trackName": "iMovie", "trackViewUrl": "https://example.test/imovie"}
        monkeypatch.setattr(app_lookup, "fetch_app_by_track_id", lambda track_id, country: fake_app)

        result = app_lookup.get_app_name(570060128, "us")
        assert result == {
            "app_id": 570060128,
            "name": "iMovie",
            "url": "https://example.test/imovie",
        }

    def test_service_error_returns_error_dict(self, monkeypatch):
        def raise_error(track_id, country):
            raise ToolError("'-5' is not a valid App Store track id")

        monkeypatch.setattr(app_lookup, "fetch_app_by_track_id", raise_error)

        result = app_lookup.get_app_name(-5, "us")
        assert "error" in result
