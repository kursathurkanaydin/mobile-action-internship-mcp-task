import httpx
import pytest

from mcp_task.clients import mobileaction


class TestGetSuccess:
    def test_returns_parsed_json(self, monkeypatch, fake_response):
        monkeypatch.setattr(
            mobileaction.httpx, "get", lambda *a, **k: fake_response(200, json_data={"ok": True})
        )
        assert mobileaction.get("/api-key") == {"ok": True}

    def test_none_valued_params_are_dropped_before_request(self, monkeypatch, fake_response):
        captured = {}

        def fake_get(url, params=None, timeout=None):
            captured["params"] = params
            return fake_response(200, json_data={})

        monkeypatch.setattr(mobileaction.httpx, "get", fake_get)
        mobileaction.get("/path", params={"keywords": "a", "date": None})

        assert "date" not in captured["params"]
        assert captured["params"]["keywords"] == "a"

    def test_api_token_is_always_appended(self, monkeypatch, fake_response):
        captured = {}

        def fake_get(url, params=None, timeout=None):
            captured["params"] = params
            return fake_response(200, json_data={})

        monkeypatch.setattr(mobileaction.httpx, "get", fake_get)
        mobileaction.get("/path")

        assert captured["params"]["token"] == mobileaction.MOBILEACTION_API_KEY

    def test_empty_body_returns_none_instead_of_raising(self, monkeypatch, fake_response):
        # e.g. the Google Play app-detail endpoint returns 204 with no body
        # for an unrecognized package id, rather than a 404.
        monkeypatch.setattr(mobileaction.httpx, "get", lambda *a, **k: fake_response(204))
        assert mobileaction.get("/path") is None


class TestGetHttpErrors:
    @pytest.mark.parametrize(
        "status_code, expected_snippet",
        [
            (401, "Authentication failed"),
            (403, "Access denied"),
            (404, "Not found"),
            (429, "Rate limit"),
            (500, "unexpected error"),
        ],
    )
    def test_error_status_codes_raise_with_clean_message(
        self, monkeypatch, fake_response, status_code, expected_snippet
    ):
        monkeypatch.setattr(
            mobileaction.httpx,
            "get",
            lambda *a, **k: fake_response(status_code, json_data={"detail": "nope"}),
        )

        with pytest.raises(mobileaction.MobileActionAPIError) as exc_info:
            mobileaction.get("/path")

        assert expected_snippet in exc_info.value.message
        assert exc_info.value.status_code == status_code

    def test_falls_back_to_raw_text_when_body_is_not_json(self, monkeypatch, fake_response):
        response = fake_response(500, json_data=None, text="<html>server error</html>")
        monkeypatch.setattr(mobileaction.httpx, "get", lambda *a, **k: response)

        with pytest.raises(mobileaction.MobileActionAPIError) as exc_info:
            mobileaction.get("/path")

        assert "server error" in exc_info.value.message


class TestGetNetworkErrors:
    def test_request_error_raises_clean_message(self, monkeypatch):
        def raise_network_error(*args, **kwargs):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(mobileaction.httpx, "get", raise_network_error)

        with pytest.raises(mobileaction.MobileActionAPIError) as exc_info:
            mobileaction.get("/path")

        assert "Network error" in exc_info.value.message
        assert exc_info.value.status_code is None
