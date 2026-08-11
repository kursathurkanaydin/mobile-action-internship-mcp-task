import httpx
import pytest

from mcp_task import credit_tracking
from mcp_task.clients import mobileaction


class TestGetSuccess:
    def test_returns_parsed_json(self, monkeypatch, fake_response):
        monkeypatch.setattr(
            mobileaction.httpx, "get", lambda *a, **k: fake_response(200, json_data={"ok": True})
        )
        assert mobileaction.get("/api-key") == {"ok": True}

    def test_raw_true_returns_text_instead_of_parsing_json(self, monkeypatch, fake_response):
        # app-match replies with a bare text/plain body ("com.facebook.katana"),
        # not JSON - response.json() would raise on it.
        monkeypatch.setattr(
            mobileaction.httpx, "get", lambda *a, **k: fake_response(200, text="com.facebook.katana")
        )
        assert mobileaction.get("/path", raw=True) == "com.facebook.katana"

    def test_credit_headers_are_recorded_via_credit_tracking(self, monkeypatch, fake_response):
        credit_tracking.reset()
        headers = {"X-Credit-Cost": "10", "X-Credit-Remaining": "48230"}
        monkeypatch.setattr(
            mobileaction.httpx, "get", lambda *a, **k: fake_response(200, json_data={"ok": True}, headers=headers)
        )
        mobileaction.get("/path")

        assert credit_tracking.pop() == {"credit_cost": 10, "credit_remaining": 48230}

    def test_no_credit_headers_leaves_credit_tracking_untouched(self, monkeypatch, fake_response):
        credit_tracking.reset()
        monkeypatch.setattr(
            mobileaction.httpx, "get", lambda *a, **k: fake_response(200, json_data={"ok": True})
        )
        mobileaction.get("/path")

        assert credit_tracking.pop() is None

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

    def test_404_status_derives_not_found_error_type(self, monkeypatch, fake_response):
        monkeypatch.setattr(mobileaction.httpx, "get", lambda *a, **k: fake_response(404, json_data={}))

        with pytest.raises(mobileaction.MobileActionAPIError) as exc_info:
            mobileaction.get("/path")

        assert exc_info.value.error_type == "not_found"

    @pytest.mark.parametrize("status_code", [401, 403, 429, 500])
    def test_non_404_status_derives_upstream_api_error_type(self, monkeypatch, fake_response, status_code):
        monkeypatch.setattr(mobileaction.httpx, "get", lambda *a, **k: fake_response(status_code, json_data={}))

        with pytest.raises(mobileaction.MobileActionAPIError) as exc_info:
            mobileaction.get("/path")

        assert exc_info.value.error_type == "upstream_api"

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
        assert exc_info.value.error_type == "network"


class TestPostSuccess:
    def test_returns_parsed_json(self, monkeypatch, fake_response):
        monkeypatch.setattr(
            mobileaction.httpx, "post", lambda *a, **k: fake_response(200, json_data={"ok": True})
        )
        assert mobileaction.post("/api-key") == {"ok": True}

    def test_credit_headers_are_recorded_via_credit_tracking(self, monkeypatch, fake_response):
        credit_tracking.reset()
        headers = {"X-Credit-Cost": "20", "X-Credit-Remaining": "100"}
        monkeypatch.setattr(
            mobileaction.httpx, "post", lambda *a, **k: fake_response(200, json_data={"ok": True}, headers=headers)
        )
        mobileaction.post("/path")

        assert credit_tracking.pop() == {"credit_cost": 20, "credit_remaining": 100}

    def test_json_body_is_forwarded_as_is(self, monkeypatch, fake_response):
        captured = {}

        def fake_post(url, params=None, json=None, timeout=None):
            captured["json"] = json
            return fake_response(200, json_data={})

        monkeypatch.setattr(mobileaction.httpx, "post", fake_post)
        mobileaction.post("/path", json=[123, 456])

        assert captured["json"] == [123, 456]

    def test_none_valued_params_are_dropped_before_request(self, monkeypatch, fake_response):
        captured = {}

        def fake_post(url, params=None, json=None, timeout=None):
            captured["params"] = params
            return fake_response(200, json_data={})

        monkeypatch.setattr(mobileaction.httpx, "post", fake_post)
        mobileaction.post("/path", params={"countries": "US", "startDate": None})

        assert "startDate" not in captured["params"]
        assert captured["params"]["countries"] == "US"

    def test_api_token_is_always_appended(self, monkeypatch, fake_response):
        captured = {}

        def fake_post(url, params=None, json=None, timeout=None):
            captured["params"] = params
            return fake_response(200, json_data={})

        monkeypatch.setattr(mobileaction.httpx, "post", fake_post)
        mobileaction.post("/path")

        assert captured["params"]["token"] == mobileaction.MOBILEACTION_API_KEY

    def test_empty_body_returns_none_instead_of_raising(self, monkeypatch, fake_response):
        monkeypatch.setattr(mobileaction.httpx, "post", lambda *a, **k: fake_response(204))
        assert mobileaction.post("/path") is None


class TestPostHttpErrors:
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
            "post",
            lambda *a, **k: fake_response(status_code, json_data={"detail": "nope"}),
        )

        with pytest.raises(mobileaction.MobileActionAPIError) as exc_info:
            mobileaction.post("/path")

        assert expected_snippet in exc_info.value.message
        assert exc_info.value.status_code == status_code


class TestPostNetworkErrors:
    def test_request_error_raises_clean_message(self, monkeypatch):
        def raise_network_error(*args, **kwargs):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(mobileaction.httpx, "post", raise_network_error)

        with pytest.raises(mobileaction.MobileActionAPIError) as exc_info:
            mobileaction.post("/path")

        assert "Network error" in exc_info.value.message
        assert exc_info.value.status_code is None
        assert exc_info.value.error_type == "network"
