from mcp_task.clients.mobileaction import get
from mcp_task.services.cache import cached
from mcp_task.validation.appstore import require_device, require_track_id
from mcp_task.validation.common import (
    require_country_code,
    require_date,
    require_date_range,
    require_keyword_list,
    require_positive_int,
    require_text,
)


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

    cache_key = f"mcp:appstore:keyword_ranking:{track_id}:{country_code}:{keywords}:{date}"
    return cached(cache_key, fetch)


def fetch_top_keywords(
    track_id: int, country_code: str, date: str, device: str | None, limit: int | None
) -> dict:
    """Validate inputs and fetch the keywords bringing an app the most search volume."""
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    date = require_date(date, "date")
    device = require_device(device, required=False)
    limit = require_positive_int(limit, "limit")

    cache_key = f"mcp:appstore:top_keywords:{track_id}:{country_code}:{date}:{device or 'all'}:{limit or 'default'}"
    return cached(
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

    Shared by get_appstore_keyword_ranking_history, plot_appstore_keyword_ranking_history, and
    compare_appstore_keyword_ranking_history so they stay in sync on request shape and
    validation. Raises InputValidationError on a bad input or
    MobileActionAPIError on failure; returns the raw list of per-day,
    per-device {trackId, keyword, rank, countryCode, date, appKind} entries.
    Both dates are always concrete and in the past, so this is always cached.
    """
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")
    require_date_range(start_date, end_date, max_days=30)

    cache_key = f"mcp:appstore:keyword_ranking_history:{track_id}:{country_code}:{keyword}:{start_date}:{end_date}"
    return cached(
        cache_key,
        lambda: get(
            f"/appstore-keyword-ranking/{track_id}/{country_code}/{keyword}/keywordrankings",
            params={"startDate": start_date, "endDate": end_date},
        ),
    )


def fetch_keyword_ranking_history_multi(
    track_id: int,
    country_code: str,
    keywords: str,
    start_date: str,
    end_date: str,
) -> dict[str, list]:
    """Validate inputs and fetch App Store ranking history for MULTIPLE keywords, one app.

    Returns {keyword: [day entries...]}. One MobileAction request per
    keyword — unlike the single-day ranking endpoint (fetch_keyword_ranking),
    the history endpoint only accepts one keyword per call, so this can't be
    a single batched request. Reuses fetch_keyword_ranking_history per
    keyword rather than duplicating its validation/caching, at the cost of
    re-validating track_id/country_code/date_range once per keyword (cheap —
    no extra API calls, since those are pure string checks).
    """
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    require_date_range(start_date, end_date, max_days=30)
    keyword_list = require_keyword_list(keywords)

    return {
        keyword: fetch_keyword_ranking_history(track_id, country_code, keyword, start_date, end_date)
        for keyword in keyword_list
    }


def fetch_keyword_metadata(country_code: str, keyword: str) -> dict:
    """Validate inputs and fetch metadata for a single keyword."""
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")

    cache_key = f"mcp:appstore:keyword_metadata:{country_code}:{keyword}"
    return cached(
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

    cache_key = f"mcp:appstore:apps_for_keyword:{country_code}:{keyword}"
    return cached(
        cache_key,
        lambda: get(
            f"/appstore-keyword-ranking/{country_code}/keyword-apps",
            params={"keyword": keyword},
        ),
    )


def fetch_organic_keywords(track_id: int, country_code: str, device: str, date: str, limit: int) -> dict:
    """Validate inputs and fetch the full organic keyword list for an app.

    limit isn't part of the cache key or the API call itself — the API
    always returns the full list regardless, and the caller (get_appstore_organic_keywords)
    caps/sorts it client-side after this returns. Costs 50 credits per live
    call, so this is the endpoint that benefits most from caching.
    """
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    device = require_device(device, required=True)
    date = require_date(date, "date")
    require_positive_int(limit, "limit")

    cache_key = f"mcp:appstore:organic_keywords:{track_id}:{country_code}:{device}:{date}"
    return cached(
        cache_key,
        lambda: get(
            f"/appstore-keyword-ranking/{track_id}/{country_code}/{device}/organic-keywords",
            params={"date": date},
        ),
    )
