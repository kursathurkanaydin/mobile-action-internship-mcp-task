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

        with pytest.raises(itunes.AppLookupError, match="No app found"):
            itunes.search_app("Definitely Not A Real App", "us")

    def test_http_error_status_raises_app_lookup_error(self, monkeypatch, fake_response):
        monkeypatch.setattr(itunes.httpx, "get", lambda *a, **k: fake_response(500))

        with pytest.raises(itunes.AppLookupError, match="Failed to search"):
            itunes.search_app("Clash of Clans", "us")

    def test_network_error_raises_app_lookup_error(self, monkeypatch):
        def raise_network_error(*args, **kwargs):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(itunes.httpx, "get", raise_network_error)

        with pytest.raises(itunes.AppLookupError, match="Failed to search"):
            itunes.search_app("Clash of Clans", "us")


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
