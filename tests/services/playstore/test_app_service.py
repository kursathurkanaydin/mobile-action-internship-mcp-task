import json

import pytest
from redis.exceptions import RedisError

from mcp_task.clients.mobileaction import MobileActionAPIError
from mcp_task.errors import ToolError
from mcp_task.services import cache
from mcp_task.services.playstore import app_service as pas


def _no_call(*args, **kwargs):
    raise AssertionError("the MobileAction client should not be called for invalid input")


class _FakeRedis:
    """In-memory stand-in for redis_client so tests never touch a real Redis server."""

    def __init__(self, existing: dict | None = None, raise_on_get: bool = False, raise_on_set: bool = False):
        self._store = dict(existing or {})
        self._raise_on_get = raise_on_get
        self._raise_on_set = raise_on_set
        self.set_calls = []
        self.get_calls = []

    def get(self, key):
        self.get_calls.append(key)
        if self._raise_on_get:
            raise RedisError("simulated redis GET failure")
        return self._store.get(key)

    def set(self, key, value, ex=None):
        if self._raise_on_set:
            raise RedisError("simulated redis SET failure")
        self.set_calls.append((key, value, ex))
        self._store[key] = value


class _UntouchableRedis:
    """redis_client stand-in that fails the test if it's ever called at all."""

    def get(self, key):
        raise AssertionError("redis_client.get should not be called for this path")

    def set(self, key, value, ex=None):
        raise AssertionError("redis_client.set should not be called for this path")


class TestFetchAppByTrackId:
    """fetch_app_by_track_id delegates to fetch_apps_by_track_ids (the 1-credit
    "simple" endpoint) with a single id, instead of the 5-credit "detailed"
    endpoint — see app_service.py's docstring for why. These tests mock
    fetch_apps_by_track_ids directly rather than the HTTP layer, since that's
    the actual collaborator now.
    """

    def test_invalid_track_id_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(pas, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError):
            pas.fetch_app_by_track_id("not-a-package-name")

    def test_delegates_to_fetch_apps_by_track_ids_with_the_single_id(self, monkeypatch):
        captured = {}
        fake_app = {"trackId": "com.block.juggle", "name": "Block Blast!"}

        def fake_fetch_apps_by_track_ids(track_ids, lang_code):
            captured["track_ids"] = track_ids
            captured["lang_code"] = lang_code
            return (["com.block.juggle"], [fake_app])

        monkeypatch.setattr(pas, "fetch_apps_by_track_ids", fake_fetch_apps_by_track_ids)

        result = pas.fetch_app_by_track_id("com.block.juggle", "en")

        assert captured == {"track_ids": "com.block.juggle", "lang_code": "en"}
        assert result == fake_app

    def test_play_store_url_is_passed_through_unresolved_to_fetch_apps_by_track_ids(self, monkeypatch):
        # id/URL resolution happens inside fetch_apps_by_track_ids (via
        # require_package_name_list), not here — no need to duplicate it
        captured = {}
        url = "https://play.google.com/store/apps/details?id=com.block.juggle&hl=tr"

        def fake_fetch_apps_by_track_ids(track_ids, lang_code):
            captured["track_ids"] = track_ids
            return (["com.block.juggle"], [{"trackId": "com.block.juggle", "name": "Block Blast!"}])

        monkeypatch.setattr(pas, "fetch_apps_by_track_ids", fake_fetch_apps_by_track_ids)

        result = pas.fetch_app_by_track_id(url)

        assert captured["track_ids"] == url
        assert result == {"trackId": "com.block.juggle", "name": "Block Blast!"}

    def test_not_found_raises_mobileaction_api_error(self, monkeypatch):
        monkeypatch.setattr(pas, "fetch_apps_by_track_ids", lambda *a: (["com.does.not.exist"], []))

        with pytest.raises(MobileActionAPIError, match="Not found") as exc_info:
            pas.fetch_app_by_track_id("com.does.not.exist")
        assert exc_info.value.status_code == 404


class TestFetchAppsByName:
    def test_empty_query_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(pas, "search_apps", _no_call)
        with pytest.raises(ToolError, match="cannot be empty"):
            pas.fetch_apps_by_name("")

    def test_valid_input_delegates_with_expected_args(self, monkeypatch):
        captured = {}
        fake_apps = [{"appId": "com.whatsapp.w4b", "title": "WhatsApp Business"}]

        def fake_search_apps(query, country, lang_code):
            captured["query"] = query
            captured["country"] = country
            captured["lang_code"] = lang_code
            return fake_apps

        monkeypatch.setattr(pas, "search_apps", fake_search_apps)
        result = pas.fetch_apps_by_name("WhatsApp", "tr", "tr")

        assert captured == {"query": "WhatsApp", "country": "tr", "lang_code": "tr"}
        assert result == fake_apps

    def test_invalid_country_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(pas, "search_apps", _no_call)
        with pytest.raises(ToolError):
            pas.fetch_apps_by_name("WhatsApp", "usa")

    def test_no_results_returns_empty_list_not_an_error(self, monkeypatch):
        monkeypatch.setattr(pas, "search_apps", lambda query, country, lang_code: [])
        assert pas.fetch_apps_by_name("nonsense") == []

    def test_search_failure_propagates_as_a_tool_error(self, monkeypatch):
        # a genuine search failure (network error, Google blocking the
        # scraper) must surface, not be swallowed into an empty result
        def raise_search_error(query, country, lang_code):
            from mcp_task.clients.google_play_scraper import PlayStoreSearchError

            raise PlayStoreSearchError("Network error while searching Google Play: timeout")

        monkeypatch.setattr(pas, "search_apps", raise_search_error)
        with pytest.raises(ToolError, match="Network error"):
            pas.fetch_apps_by_name("WhatsApp")

    def test_not_cached(self, monkeypatch):
        # a live search, not a fixed id-keyed record — must never touch redis
        monkeypatch.setattr(pas, "search_apps", lambda query, country, lang_code: [])
        monkeypatch.setattr(cache, "redis_client", _UntouchableRedis())
        pas.fetch_apps_by_name("WhatsApp")


class TestFetchAppsByTrackIds:
    def test_empty_track_ids_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(pas, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError, match="cannot be empty"):
            pas.fetch_apps_by_track_ids("")

    def test_single_id_is_allowed(self, monkeypatch):
        fake_apps = [{"trackId": "com.block.juggle", "name": "Block Blast!"}]
        monkeypatch.setattr(pas, "get", lambda path, params: fake_apps)
        monkeypatch.setattr(cache, "redis_client", _FakeRedis())

        requested_ids, apps = pas.fetch_apps_by_track_ids("com.block.juggle")
        assert requested_ids == ["com.block.juggle"]
        assert apps == fake_apps

    def test_valid_input_delegates_with_expected_args(self, monkeypatch):
        captured = {}
        fake_apps = [{"trackId": "com.a"}, {"trackId": "com.b"}]

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_apps

        fake_redis = _FakeRedis()
        monkeypatch.setattr(pas, "get", fake_get)
        monkeypatch.setattr(cache, "redis_client", fake_redis)

        requested_ids, apps = pas.fetch_apps_by_track_ids(" com.a , com.b ", "tr")

        assert requested_ids == ["com.a", "com.b"]
        assert captured["path"] == "/playstore-appinfo-v2/app/simple/tr"
        assert captured["params"] == {"trackIds": "com.a,com.b"}
        assert apps == fake_apps
        assert fake_redis.set_calls[0][0] == "mcp:playstore:app_batch:tr:com.a,com.b"

    def test_more_than_batch_lookup_max_ids_raises_before_any_request(self, monkeypatch):
        from mcp_task.config import BATCH_LOOKUP_MAX_IDS

        monkeypatch.setattr(pas, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _UntouchableRedis())
        ids = ",".join(f"com.app{i}" for i in range(BATCH_LOOKUP_MAX_IDS + 1))
        with pytest.raises(ToolError, match=f"at most {BATCH_LOOKUP_MAX_IDS}"):
            pas.fetch_apps_by_track_ids(ids)

    def test_invalid_package_name_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(pas, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError):
            pas.fetch_apps_by_track_ids("com.a,not-a-package-name")

    def test_cache_hit_returns_cached_data_without_calling_the_client(self, monkeypatch):
        cache_key = "mcp:playstore:app_batch:en:com.a"
        cached_data = [{"trackId": "com.a", "name": "App A"}]
        monkeypatch.setattr(pas, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _FakeRedis(existing={cache_key: json.dumps(cached_data)}))

        requested_ids, apps = pas.fetch_apps_by_track_ids("com.a")
        assert requested_ids == ["com.a"]
        assert apps == cached_data
