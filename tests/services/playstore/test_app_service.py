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
    def test_invalid_track_id_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(pas, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError):
            pas.fetch_app_by_track_id("not-a-package-name")

    def test_valid_bare_id_delegates_with_expected_args(self, monkeypatch):
        captured = {}
        fake_app = {"trackId": "com.block.juggle", "name": "Block Blast!"}

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_app

        fake_redis = _FakeRedis()
        monkeypatch.setattr(pas, "get", fake_get)
        monkeypatch.setattr(cache, "redis_client", fake_redis)

        result = pas.fetch_app_by_track_id("com.block.juggle", "en")

        assert captured["path"] == "/playstore-appinfo-v2/app/detailed/com.block.juggle"
        assert captured["params"] == {"langCode": "en"}
        assert result == fake_app
        assert fake_redis.set_calls[0][0] == "mcp:playstore:app_detail:com.block.juggle:en"

    def test_play_store_url_is_resolved_to_its_package_id(self, monkeypatch):
        captured = {}
        fake_app = {"trackId": "com.block.juggle", "name": "Block Blast!"}

        def fake_get(path, params):
            captured["path"] = path
            return fake_app

        monkeypatch.setattr(pas, "get", fake_get)
        monkeypatch.setattr(cache, "redis_client", _FakeRedis())

        result = pas.fetch_app_by_track_id(
            "https://play.google.com/store/apps/details?id=com.block.juggle&hl=tr"
        )

        assert captured["path"] == "/playstore-appinfo-v2/app/detailed/com.block.juggle"
        assert result == fake_app

    def test_not_found_raises_mobileaction_api_error(self, monkeypatch):
        monkeypatch.setattr(pas, "get", lambda path, params: None)
        monkeypatch.setattr(cache, "redis_client", _FakeRedis())

        with pytest.raises(MobileActionAPIError, match="Not found"):
            pas.fetch_app_by_track_id("com.does.not.exist")

    def test_cache_hit_returns_cached_data_without_calling_the_client(self, monkeypatch):
        cache_key = "mcp:playstore:app_detail:com.block.juggle:en"
        cached_data = {"trackId": "com.block.juggle", "name": "Block Blast!"}
        monkeypatch.setattr(pas, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _FakeRedis(existing={cache_key: json.dumps(cached_data)}))

        result = pas.fetch_app_by_track_id("com.block.juggle", "en")
        assert result == cached_data


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
