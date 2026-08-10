import json
import logging
from typing import Callable, TypeVar

from redis.exceptions import RedisError

from mcp_task.config import redis_client

logger = logging.getLogger(__name__)

# MobileAction's keyword data is a daily batch update, so a fixed historical
# query (a specific past date/date range) never changes — caching it for a
# full day trades a little staleness at the very end of the window for a
# real reduction in repeated-query credit spend. Shared by every store's
# keyword service (App Store, Play Store, ...) so the caching behavior and
# Redis-outage handling stay identical across stores.
CACHE_TTL_SECONDS = 86400

T = TypeVar("T")


def cached(cache_key: str, fetch: Callable[[], T]) -> T:
    """Return cached JSON for cache_key if present; otherwise call fetch(), cache it, and return it.

    A Redis outage on either the read or the write degrades to calling
    fetch() directly rather than failing — caching is an optimization, not
    something a tool call should depend on to function.
    """
    try:
        cached_value = redis_client.get(cache_key)
    except RedisError:
        logger.warning("Redis unavailable reading %s, falling back to a live fetch", cache_key)
        cached_value = None

    if cached_value:
        logger.info("cache hit key=%s", cache_key)
        return json.loads(cached_value)

    data = fetch()

    try:
        redis_client.set(cache_key, json.dumps(data), ex=CACHE_TTL_SECONDS)
    except RedisError:
        logger.warning("Redis unavailable writing %s, skipping cache write", cache_key)

    return data
