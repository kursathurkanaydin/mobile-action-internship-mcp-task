from mcp_task.errors import ToolError
from mcp_task.tools.playstore import app_lookup as playstore_app_lookup


class TestGetPlaystoreAppName:
    def test_success_shapes_app_id_name_and_url(self, monkeypatch):
        fake_app = {"trackId": "com.block.juggle", "name": "Block Blast!"}
        monkeypatch.setattr(playstore_app_lookup, "fetch_app_by_track_id", lambda track_id, lang_code: fake_app)

        result = playstore_app_lookup.get_playstore_app_name("com.block.juggle", "en")
        assert result == {
            "app_id": "com.block.juggle",
            "name": "Block Blast!",
            "url": "https://play.google.com/store/apps/details?id=com.block.juggle",
        }

    def test_service_error_returns_error_dict(self, monkeypatch):
        def raise_error(track_id, lang_code):
            raise ToolError("Not found: no Google Play app exists for package id 'nope'.", status_code=404)

        monkeypatch.setattr(playstore_app_lookup, "fetch_app_by_track_id", raise_error)

        result = playstore_app_lookup.get_playstore_app_name("nope", "en")
        assert result["status_code"] == 404
        assert "error" in result


class TestGetPlaystoreAppNamesBatch:
    def test_success_shapes_apps_list_and_reports_no_missing_ids(self, monkeypatch):
        fake_apps = [
            {"trackId": "com.a", "name": "App One"},
            {"trackId": "com.b", "name": "App Two"},
        ]
        monkeypatch.setattr(
            playstore_app_lookup, "fetch_apps_by_track_ids", lambda track_ids, lang_code: (["com.a", "com.b"], fake_apps)
        )

        result = playstore_app_lookup.get_playstore_app_names_batch("com.a,com.b", "en")
        assert result == {
            "apps": [
                {"app_id": "com.a", "name": "App One", "url": "https://play.google.com/store/apps/details?id=com.a"},
                {"app_id": "com.b", "name": "App Two", "url": "https://play.google.com/store/apps/details?id=com.b"},
            ],
            "not_found_ids": [],
        }

    def test_ids_mobileaction_did_not_find_are_reported_separately(self, monkeypatch):
        fake_apps = [{"trackId": "com.a", "name": "App One"}]
        monkeypatch.setattr(
            playstore_app_lookup,
            "fetch_apps_by_track_ids",
            lambda track_ids, lang_code: (["com.a", "com.b", "com.c"], fake_apps),
        )

        result = playstore_app_lookup.get_playstore_app_names_batch("com.a,com.b,com.c", "en")
        assert result["not_found_ids"] == ["com.b", "com.c"]
        assert [app["app_id"] for app in result["apps"]] == ["com.a"]

    def test_service_error_returns_error_dict(self, monkeypatch):
        def raise_error(track_ids, lang_code):
            raise ToolError("Too many apps given at once: 400, but at most 300 are supported.")

        monkeypatch.setattr(playstore_app_lookup, "fetch_apps_by_track_ids", raise_error)

        result = playstore_app_lookup.get_playstore_app_names_batch("com.a,com.b", "en")
        assert "error" in result
