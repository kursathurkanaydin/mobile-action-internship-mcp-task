import httpx
import pytest

from mcp_task.clients import itunes


class TestSearchApp:
    def test_returns_first_result(self, monkeypatch, fake_response):
        results = [{"trackId": 529479190, "trackName": "Clash of Clans"}, {"trackId": 1}]
        monkeypatch.setattr(
            itunes.httpx, "get", lambda *a, **k: fake_response(200, json_data={"results": results})
        )

        app = itunes.search_app("Clash of Clans", "us")
        assert app == results[0]

    def test_no_results_raises_app_lookup_error(self, monkeypatch, fake_response):
        monkeypatch.setattr(
            itunes.httpx, "get", lambda *a, **k: fake_response(200, json_data={"results": []})
        )

        with pytest.raises(itunes.AppLookupError, match="No app found") as exc_info:
            itunes.search_app("Definitely Not A Real App", "us")
        assert exc_info.value.error_type == "not_found"

    def test_http_error_status_raises_app_lookup_error(self, monkeypatch, fake_response):
        monkeypatch.setattr(itunes.httpx, "get", lambda *a, **k: fake_response(500))

        with pytest.raises(itunes.AppLookupError, match="Failed to search") as exc_info:
            itunes.search_app("Clash of Clans", "us")
        assert exc_info.value.error_type == "network"

    def test_network_error_raises_app_lookup_error(self, monkeypatch):
        def raise_network_error(*args, **kwargs):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(itunes.httpx, "get", raise_network_error)

        with pytest.raises(itunes.AppLookupError, match="Failed to search") as exc_info:
            itunes.search_app("Clash of Clans", "us")
        assert exc_info.value.error_type == "network"


class TestLookupApp:
    def test_returns_first_result(self, monkeypatch, fake_response):
        results = [{"trackId": 570060128, "trackName": "iMovie"}]
        monkeypatch.setattr(
            itunes.httpx, "get", lambda *a, **k: fake_response(200, json_data={"results": results})
        )

        app = itunes.lookup_app(570060128, "us")
        assert app == results[0]

    def test_no_results_raises_app_lookup_error(self, monkeypatch, fake_response):
        monkeypatch.setattr(
            itunes.httpx, "get", lambda *a, **k: fake_response(200, json_data={"results": []})
        )

        with pytest.raises(itunes.AppLookupError, match="No app found"):
            itunes.lookup_app(1, "us")

    def test_http_error_status_raises_app_lookup_error(self, monkeypatch, fake_response):
        monkeypatch.setattr(itunes.httpx, "get", lambda *a, **k: fake_response(404))

        with pytest.raises(itunes.AppLookupError, match="Failed to look up"):
            itunes.lookup_app(1, "us")


class TestLookupApps:
    def test_joins_ids_with_commas_and_returns_all_results(self, monkeypatch, fake_response):
        captured = {}
        results = [{"trackId": 1, "trackName": "App One"}, {"trackId": 2, "trackName": "App Two"}]

        def fake_get(url, params=None, timeout=None):
            captured["params"] = params
            return fake_response(200, json_data={"results": results})

        monkeypatch.setattr(itunes.httpx, "get", fake_get)

        apps = itunes.lookup_apps([1, 2, 3], "us")

        assert captured["params"]["id"] == "1,2,3"
        assert apps == results

    def test_ids_itunes_does_not_recognize_are_simply_absent_no_error(self, monkeypatch, fake_response):
        # only 1 of the 3 requested ids came back -> not an error, caller diffs it
        monkeypatch.setattr(
            itunes.httpx, "get", lambda *a, **k: fake_response(200, json_data={"results": [{"trackId": 1}]})
        )

        assert itunes.lookup_apps([1, 2, 3], "us") == [{"trackId": 1}]

    def test_no_results_at_all_returns_empty_list_not_an_error(self, monkeypatch, fake_response):
        monkeypatch.setattr(
            itunes.httpx, "get", lambda *a, **k: fake_response(200, json_data={"results": []})
        )

        assert itunes.lookup_apps([1, 2], "us") == []

    def test_http_error_status_raises_app_lookup_error(self, monkeypatch, fake_response):
        monkeypatch.setattr(itunes.httpx, "get", lambda *a, **k: fake_response(500))

        with pytest.raises(itunes.AppLookupError, match="Failed to look up"):
            itunes.lookup_apps([1, 2], "us")

    def test_network_error_raises_app_lookup_error(self, monkeypatch):
        def raise_network_error(*args, **kwargs):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(itunes.httpx, "get", raise_network_error)

        with pytest.raises(itunes.AppLookupError, match="Failed to look up"):
            itunes.lookup_apps([1, 2], "us")
