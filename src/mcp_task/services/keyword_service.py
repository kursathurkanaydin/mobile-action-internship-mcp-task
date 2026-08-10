import json
import logging
from typing import Callable, TypeVar

from redis.exceptions import RedisError

from mcp_task.clients.mobileaction import get
from mcp_task.config import redis_client
from mcp_task.validation import (
    require_country_code,
    require_date,
    require_date_range,
    require_device,
    require_positive_int,
    require_text,
    require_track_id,
)

logger = logging.getLogger(__name__)

# MobileAction's keyword data is a daily batch update, so a fixed historical
# query (a specific past date/date range) never changes — caching it for a
# full day trades a little staleness at the very end of the window for a
# real reduction in repeated-query credit spend.
_CACHE_TTL_SECONDS = 86400

T = TypeVar("T")


def _cached(cache_key: str, fetch: Callable[[], T]) -> T:
    """Return cached JSON for cache_key if present; otherwise call fetch(), cache it, and return it.

    A Redis outage on either the read or the write degrades to calling
    fetch() directly rather than failing — caching is an optimization, not
    something a tool call should depend on to function.
    """
    try:
        cached = redis_client.get(cache_key)
    except RedisError:
        logger.warning("Redis unavailable reading %s, falling back to a live fetch", cache_key)
        cached = None

    if cached:
        logger.info("cache hit key=%s", cache_key)
        return json.loads(cached)

    data = fetch()

    try:
        redis_client.set(cache_key, json.dumps(data), ex=_CACHE_TTL_SECONDS)
    except RedisError:
        logger.warning("Redis unavailable writing %s, skipping cache write", cache_key)

    return data


def fetch_keyword_ranking(track_id: int, country_code: str, keywords: str, date: str | None) -> dict:
    """Validate inputs and fetch current keyword ranking(s) for an app.

    Only cached when an explicit date is given. Without one, "current" means
    "whatever MobileAction's most recent day is" — a moving target that a
    fixed cache key can't safely represent, so that case always fetches live.
    """
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    keywords = require_text(keywords, "keywords")
    if date is not None:
        date = require_date(date, "date")

    def fetch():
        return get(
            f"/appstore-keyword-ranking/{track_id}/{country_code}/keywordrankings",
            params={"keywords": keywords, "date": date},
        )

    if date is None:
        return fetch()

    cache_key = f"mcp:keyword_ranking:{track_id}:{country_code}:{keywords}:{date}"
    return _cached(cache_key, fetch)


def fetch_top_keywords(
    track_id: int, country_code: str, date: str, device: str | None, limit: int | None
) -> dict:
    """Validate inputs and fetch the keywords bringing an app the most search volume."""
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    date = require_date(date, "date")
    device = require_device(device, required=False)
    limit = require_positive_int(limit, "limit")

    cache_key = f"mcp:top_keywords:{track_id}:{country_code}:{date}:{device or 'all'}:{limit or 'default'}"
    return _cached(
        cache_key,
        lambda: get(
            f"/appstore-keyword-ranking/{track_id}/{country_code}/top-keywords",
            params={"date": date, "device": device, "limit": limit},
        ),
    )


def fetch_keyword_ranking_history(
    track_id: int,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> list:
    """Validate inputs and fetch App Store keyword ranking history for a date range.

    Shared by get_keyword_ranking_history, plot_keyword_ranking_history, and
    compare_keyword_ranking_history so they stay in sync on request shape and
    validation. Raises InputValidationError on a bad input or
    MobileActionAPIError on failure; returns the raw list of per-day,
    per-device {trackId, keyword, rank, countryCode, date, appKind} entries.
    Both dates are always concrete and in the past, so this is always cached.
    """
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")
    require_date_range(start_date, end_date, max_days=30)

    cache_key = f"mcp:keyword_ranking_history:{track_id}:{country_code}:{keyword}:{start_date}:{end_date}"
    return _cached(
        cache_key,
        lambda: get(
            f"/appstore-keyword-ranking/{track_id}/{country_code}/{keyword}/keywordrankings",
            params={"startDate": start_date, "endDate": end_date},
        ),
    )


def fetch_keyword_metadata(country_code: str, keyword: str) -> dict:
    """Validate inputs and fetch metadata for a single keyword."""
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")

    cache_key = f"mcp:keyword_metadata:{country_code}:{keyword}"
    return _cached(
        cache_key,
        lambda: get(
            f"/appstore-keyword-ranking/{country_code}/keyword-metadata",
            params={"keyword": keyword},
        ),
    )


def fetch_apps_for_keyword(country_code: str, keyword: str) -> dict:
    """Validate inputs and fetch the apps that rank for a keyword."""
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")

    cache_key = f"mcp:apps_for_keyword:{country_code}:{keyword}"
    return _cached(
        cache_key,
        lambda: get(
            f"/appstore-keyword-ranking/{country_code}/keyword-apps",
            params={"keyword": keyword},
        ),
    )


def fetch_organic_keywords(track_id: int, country_code: str, device: str, date: str, limit: int) -> dict:
    """Validate inputs and fetch the full organic keyword list for an app.

    limit isn't part of the cache key or the API call itself — the API
    always returns the full list regardless, and the caller (get_organic_keywords)
    caps/sorts it client-side after this returns. Costs 50 credits per live
    call, so this is the endpoint that benefits most from caching.
    """
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    device = require_device(device, required=True)
    date = require_date(date, "date")
    require_positive_int(limit, "limit")

    cache_key = f"mcp:organic_keywords:{track_id}:{country_code}:{device}:{date}"
    return _cached(
        cache_key,
        lambda: get(
            f"/appstore-keyword-ranking/{track_id}/{country_code}/{device}/organic-keywords",
            params={"date": date},
        ),
    )
