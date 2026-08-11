import json

import pytest
from redis.exceptions import RedisError

from mcp_task.errors import ToolError
from mcp_task.services import cache
from mcp_task.services.other import app_service


class _FakeRedis:
    """In-memory stand-in for redis_client so tests never touch a real Redis server."""

    def __init__(self, existing: dict | None = None):
        self._store = dict(existing or {})
        self.set_calls = []

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ex=None):
        self.set_calls.append((key, value, ex))
        self._store[key] = value


class _UntouchableRedis:
    def get(self, key):
        raise RedisError("should not be called")

    def set(self, key, value, ex=None):
        raise RedisError("should not be called")


def _no_call(*args, **kwargs):
    raise AssertionError("the MobileAction client should not be called for invalid input")


class TestFetchAppMatch:
    def test_invalid_store_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(app_service, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError):
            app_service.fetch_app_match("android", "284882215")

    def test_empty_track_id_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(app_service, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError):
            app_service.fetch_app_match("ios", "")

    def test_valid_input_calls_get_with_raw_true(self, monkeypatch):
        captured = {}

        def fake_get(path, params=None, raw=False):
            captured["path"] = path
            captured["params"] = params
            captured["raw"] = raw
            return "com.facebook.katana"

        monkeypatch.setattr(app_service, "get", fake_get)
        monkeypatch.setattr(cache, "redis_client", _FakeRedis())

        result = app_service.fetch_app_match("ios", "284882215")

        assert captured == {"path": "/app-match/app/ios", "params": {"trackId": "284882215"}, "raw": True}
        assert result == "com.facebook.katana"

    def test_store_is_normalized_and_included_in_cache_key(self, monkeypatch):
        fake_redis = _FakeRedis()
        monkeypatch.setattr(app_service, "get", lambda path, params=None, raw=False: "com.facebook.katana")
        monkeypatch.setattr(cache, "redis_client", fake_redis)

        app_service.fetch_app_match(" IOS ", "284882215")

        assert fake_redis.set_calls[0][0] == "mcp:other:app_match:ios:284882215"

    def test_cache_hit_returns_cached_value_without_calling_the_client(self, monkeypatch):
        cache_key = "mcp:other:app_match:ios:284882215"
        monkeypatch.setattr(app_service, "get", _no_call)
        monkeypatch.setattr(cache, "redis_client", _FakeRedis(existing={cache_key: json.dumps("com.facebook.katana")}))

        assert app_service.fetch_app_match("ios", "284882215") == "com.facebook.katana"
