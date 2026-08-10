import json

import pytest
from redis.exceptions import RedisError

from mcp_task.errors import ToolError
from mcp_task.services import keyword_service as ks


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


class TestFetchKeywordRanking:
    def test_invalid_track_id_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        with pytest.raises(ToolError):
            ks.fetch_keyword_ranking(0, "US", "strategy", None)

    def test_without_a_date_never_touches_redis_and_always_calls_the_client(self, monkeypatch):
        monkeypatch.setattr(ks, "get", lambda path, params: [{"keyword": "strategy", "rank": 5}])
        monkeypatch.setattr(ks, "redis_client", _UntouchableRedis())

        result = ks.fetch_keyword_ranking(529479190, "us", "strategy", None)
        assert result == [{"keyword": "strategy", "rank": 5}]

    def test_with_a_date_is_cached(self, monkeypatch):
        captured = {}
        fake_data = [{"keyword": "strategy", "rank": 5}]

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_data

        fake_redis = _FakeRedis()
        monkeypatch.setattr(ks, "get", fake_get)
        monkeypatch.setattr(ks, "redis_client", fake_redis)

        result = ks.fetch_keyword_ranking(529479190, "us", "strategy", "2026-07-01")

        assert captured["path"] == "/appstore-keyword-ranking/529479190/US/keywordrankings"
        assert captured["params"] == {"keywords": "strategy", "date": "2026-07-01"}
        assert result == fake_data
        assert len(fake_redis.set_calls) == 1
        assert fake_redis.set_calls[0][0] == "mcp:keyword_ranking:529479190:US:strategy:2026-07-01"

    def test_with_a_date_cache_hit_skips_the_client(self, monkeypatch):
        cache_key = "mcp:keyword_ranking:529479190:US:strategy:2026-07-01"
        cached_data = [{"keyword": "strategy", "rank": 5}]
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _FakeRedis(existing={cache_key: json.dumps(cached_data)}))

        result = ks.fetch_keyword_ranking(529479190, "us", "strategy", "2026-07-01")
        assert result == cached_data

    def test_optional_date_is_validated_when_provided(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError, match="date"):
            ks.fetch_keyword_ranking(529479190, "US", "strategy", "not-a-date")


class TestFetchTopKeywords:
    def test_invalid_limit_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError):
            ks.fetch_top_keywords(529479190, "US", "2026-07-01", None, -5)

    def test_cache_miss_calls_client_and_writes_the_cache(self, monkeypatch):
        captured = {}
        fake_data = [{"keyword": "game", "searchVolume": 100, "rank": 3}]

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_data

        fake_redis = _FakeRedis()
        monkeypatch.setattr(ks, "get", fake_get)
        monkeypatch.setattr(ks, "redis_client", fake_redis)

        result = ks.fetch_top_keywords(529479190, "US", "2026-07-01", "iphone", 50)

        assert captured["path"] == "/appstore-keyword-ranking/529479190/US/top-keywords"
        assert captured["params"] == {"date": "2026-07-01", "device": "IPHONE", "limit": 50}
        assert result == fake_data

        assert len(fake_redis.set_calls) == 1
        cache_key, cached_json, ttl = fake_redis.set_calls[0]
        assert cache_key == "mcp:top_keywords:529479190:US:2026-07-01:IPHONE:50"
        assert json.loads(cached_json) == fake_data
        assert ttl == ks._CACHE_TTL_SECONDS

    def test_cache_hit_returns_cached_data_without_calling_the_client(self, monkeypatch):
        cache_key = "mcp:top_keywords:529479190:US:2026-07-01:all:default"
        cached_data = [{"keyword": "game", "searchVolume": 100, "rank": 3}]
        fake_redis = _FakeRedis(existing={cache_key: json.dumps(cached_data)})

        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", fake_redis)

        result = ks.fetch_top_keywords(529479190, "US", "2026-07-01", None, None)
        assert result == cached_data

    def test_redis_read_failure_falls_back_to_a_live_fetch(self, monkeypatch):
        fake_data = [{"keyword": "game", "rank": 3}]
        monkeypatch.setattr(ks, "get", lambda path, params: fake_data)
        monkeypatch.setattr(ks, "redis_client", _FakeRedis(raise_on_get=True))

        result = ks.fetch_top_keywords(529479190, "US", "2026-07-01", None, None)
        assert result == fake_data

    def test_redis_write_failure_does_not_fail_the_call(self, monkeypatch):
        fake_data = [{"keyword": "game", "rank": 3}]
        monkeypatch.setattr(ks, "get", lambda path, params: fake_data)
        monkeypatch.setattr(ks, "redis_client", _FakeRedis(raise_on_set=True))

        result = ks.fetch_top_keywords(529479190, "US", "2026-07-01", None, None)
        assert result == fake_data


class TestFetchKeywordRankingHistory:
    def test_invalid_date_range_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError, match="before"):
            ks.fetch_keyword_ranking_history(529479190, "US", "strategy", "2026-07-20", "2026-07-01")

    def test_cache_miss_calls_client_and_writes_the_cache(self, monkeypatch):
        captured = {}
        fake_history = [{"date": "2026-07-01T00:00:00", "rank": 10, "appKind": "IPHONE"}]

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_history

        fake_redis = _FakeRedis()
        monkeypatch.setattr(ks, "get", fake_get)
        monkeypatch.setattr(ks, "redis_client", fake_redis)

        result = ks.fetch_keyword_ranking_history(529479190, "US", "strategy", "2026-07-01", "2026-07-01")

        assert captured["path"] == "/appstore-keyword-ranking/529479190/US/strategy/keywordrankings"
        assert captured["params"] == {"startDate": "2026-07-01", "endDate": "2026-07-01"}
        assert result == fake_history
        assert len(fake_redis.set_calls) == 1
        assert fake_redis.set_calls[0][0] == "mcp:keyword_ranking_history:529479190:US:strategy:2026-07-01:2026-07-01"

    def test_cache_hit_returns_cached_data_without_calling_the_client(self, monkeypatch):
        cache_key = "mcp:keyword_ranking_history:529479190:US:strategy:2026-07-01:2026-07-01"
        cached_data = [{"date": "2026-07-01T00:00:00", "rank": 10, "appKind": "IPHONE"}]
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _FakeRedis(existing={cache_key: json.dumps(cached_data)}))

        result = ks.fetch_keyword_ranking_history(529479190, "US", "strategy", "2026-07-01", "2026-07-01")
        assert result == cached_data


class TestFetchKeywordMetadata:
    def test_empty_keyword_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError, match="cannot be empty"):
            ks.fetch_keyword_metadata("US", "")

    def test_cache_miss_calls_client_and_writes_the_cache(self, monkeypatch):
        captured = {}
        fake_data = {"searchVolume": 500, "popularity": 80}

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_data

        fake_redis = _FakeRedis()
        monkeypatch.setattr(ks, "get", fake_get)
        monkeypatch.setattr(ks, "redis_client", fake_redis)

        result = ks.fetch_keyword_metadata("US", "meditation")

        assert captured["path"] == "/appstore-keyword-ranking/US/keyword-metadata"
        assert captured["params"] == {"keyword": "meditation"}
        assert result == fake_data
        assert fake_redis.set_calls[0][0] == "mcp:keyword_metadata:US:meditation"

    def test_cache_hit_returns_cached_data_without_calling_the_client(self, monkeypatch):
        cache_key = "mcp:keyword_metadata:US:meditation"
        cached_data = {"searchVolume": 500, "popularity": 80}
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _FakeRedis(existing={cache_key: json.dumps(cached_data)}))

        result = ks.fetch_keyword_metadata("US", "meditation")
        assert result == cached_data


class TestFetchAppsForKeyword:
    def test_invalid_country_code_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError):
            ks.fetch_apps_for_keyword("", "meditation")

    def test_cache_miss_calls_client_and_writes_the_cache(self, monkeypatch):
        captured = {}
        fake_data = [{"trackId": 1}, {"trackId": 2}]

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_data

        fake_redis = _FakeRedis()
        monkeypatch.setattr(ks, "get", fake_get)
        monkeypatch.setattr(ks, "redis_client", fake_redis)

        result = ks.fetch_apps_for_keyword("US", "meditation")

        assert captured["path"] == "/appstore-keyword-ranking/US/keyword-apps"
        assert captured["params"] == {"keyword": "meditation"}
        assert result == fake_data
        assert fake_redis.set_calls[0][0] == "mcp:apps_for_keyword:US:meditation"

    def test_cache_hit_returns_cached_data_without_calling_the_client(self, monkeypatch):
        cache_key = "mcp:apps_for_keyword:US:meditation"
        cached_data = [{"trackId": 1}, {"trackId": 2}]
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _FakeRedis(existing={cache_key: json.dumps(cached_data)}))

        result = ks.fetch_apps_for_keyword("US", "meditation")
        assert result == cached_data


class TestFetchOrganicKeywords:
    def test_invalid_device_raises_before_any_request(self, monkeypatch):
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _UntouchableRedis())
        with pytest.raises(ToolError):
            ks.fetch_organic_keywords(529479190, "US", "ANDROID", "2026-07-01", 100)

    def test_cache_miss_calls_client_and_writes_the_cache(self, monkeypatch):
        captured = {}
        fake_data = {"rankings": []}

        def fake_get(path, params):
            captured["path"] = path
            captured["params"] = params
            return fake_data

        fake_redis = _FakeRedis()
        monkeypatch.setattr(ks, "get", fake_get)
        monkeypatch.setattr(ks, "redis_client", fake_redis)

        result = ks.fetch_organic_keywords(529479190, "US", "iphone", "2026-07-01", 100)

        assert captured["path"] == "/appstore-keyword-ranking/529479190/US/IPHONE/organic-keywords"
        assert captured["params"] == {"date": "2026-07-01"}
        assert result == fake_data
        assert fake_redis.set_calls[0][0] == "mcp:organic_keywords:529479190:US:IPHONE:2026-07-01"

    def test_cache_key_does_not_depend_on_limit(self, monkeypatch):
        # limit only affects client-side capping in the tool layer, not the
        # API call itself, so two different limits must hit the same cache entry
        fake_redis = _FakeRedis()
        monkeypatch.setattr(ks, "get", lambda path, params: {"rankings": []})
        monkeypatch.setattr(ks, "redis_client", fake_redis)

        ks.fetch_organic_keywords(529479190, "US", "iphone", "2026-07-01", 50)
        ks.fetch_organic_keywords(529479190, "US", "iphone", "2026-07-01", 999)

        assert len(fake_redis.set_calls) == 1  # 2nd call was a cache hit, no 2nd write
        assert len(fake_redis.get_calls) == 2

    def test_cache_hit_returns_cached_data_without_calling_the_client(self, monkeypatch):
        cache_key = "mcp:organic_keywords:529479190:US:IPHONE:2026-07-01"
        cached_data = {"rankings": [{"keyword": "clan", "rank": 1}]}
        monkeypatch.setattr(ks, "get", _no_call)
        monkeypatch.setattr(ks, "redis_client", _FakeRedis(existing={cache_key: json.dumps(cached_data)}))

        result = ks.fetch_organic_keywords(529479190, "US", "iphone", "2026-07-01", 100)
        assert result == cached_data
