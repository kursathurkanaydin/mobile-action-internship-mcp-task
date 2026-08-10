from urllib.error import URLError

import pytest
from google_play_scraper.exceptions import ExtraHTTPError, NotFoundError

from mcp_task.clients import google_play_scraper as gps


class TestSearchApps:
    def test_drops_entries_with_no_appid(self, monkeypatch):
        # e.g. Google's "top card" result the underlying scraper can't extract an id for
        results = [
            {"appId": None, "title": "WhatsApp Messenger"},
            {"appId": "com.whatsapp.w4b", "title": "WhatsApp Business"},
        ]
        monkeypatch.setattr(gps, "_search", lambda query, n_hits, lang, country: results)

        apps = gps.search_apps("WhatsApp", "us", "en")
        assert apps == [{"appId": "com.whatsapp.w4b", "title": "WhatsApp Business"}]

    def test_passes_through_query_and_params(self, monkeypatch):
        captured = {}

        def fake_search(query, n_hits, lang, country):
            captured["query"] = query
            captured["n_hits"] = n_hits
            captured["lang"] = lang
            captured["country"] = country
            return []

        monkeypatch.setattr(gps, "_search", fake_search)
        gps.search_apps("Duolingo", "tr", "tr", n_hits=5)

        assert captured == {"query": "Duolingo", "n_hits": 5, "lang": "tr", "country": "tr"}

    def test_not_found_error_returns_empty_list(self, monkeypatch):
        def raise_not_found(*a, **k):
            raise NotFoundError("no results")

        monkeypatch.setattr(gps, "_search", raise_not_found)
        assert gps.search_apps("nonsense", "us", "en") == []

    def test_library_parsing_crash_returns_empty_list_instead_of_raising(self, monkeypatch):
        # observed live: a zero-result query can raise TypeError inside the
        # library instead of returning [] — must degrade gracefully, not crash
        def raise_type_error(*a, **k):
            raise TypeError("'NoneType' object is not subscriptable")

        monkeypatch.setattr(gps, "_search", raise_type_error)
        assert gps.search_apps("xyz123nonexistent", "us", "en") == []

    def test_no_results_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(gps, "_search", lambda query, n_hits, lang, country: [])
        assert gps.search_apps("nonsense", "us", "en") == []

    def test_network_error_raises_play_store_search_error_not_empty_list(self, monkeypatch):
        # a genuine failure must not look identical to "zero matches" —
        # returning [] here would silently misrepresent an unknown result
        def raise_network_error(*a, **k):
            raise URLError("Name or service not known")

        monkeypatch.setattr(gps, "_search", raise_network_error)
        with pytest.raises(gps.PlayStoreSearchError, match="Network error") as exc_info:
            gps.search_apps("WhatsApp", "us", "en")
        assert exc_info.value.error_type == "network"

    def test_extra_http_error_raises_play_store_search_error(self, monkeypatch):
        def raise_http_error(*a, **k):
            raise ExtraHTTPError("Status code 429 returned")

        monkeypatch.setattr(gps, "_search", raise_http_error)
        with pytest.raises(gps.PlayStoreSearchError, match="Google Play search failed") as exc_info:
            gps.search_apps("WhatsApp", "us", "en")
        assert exc_info.value.error_type == "upstream_api"
