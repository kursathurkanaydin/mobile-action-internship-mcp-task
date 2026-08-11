from mcp_task.errors import ToolError
from mcp_task.tools.other import app_service


class TestGetAppMatch:
    def test_success_shapes_matching_track_id(self, monkeypatch):
        monkeypatch.setattr(app_service, "fetch_app_match", lambda store, track_id: "com.facebook.katana")

        result = app_service.get_app_match("ios", "284882215")
        assert result == {"matching_track_id": "com.facebook.katana"}

    def test_service_error_returns_error_dict(self, monkeypatch):
        def raise_error(store, track_id):
            raise ToolError("'store' is not a valid store — it must be 'ios' or 'play'.", error_type="validation")

        monkeypatch.setattr(app_service, "fetch_app_match", raise_error)

        result = app_service.get_app_match("android", "284882215")
        assert result["error_type"] == "validation"
        assert "error" in result
