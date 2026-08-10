from mcp_task.clients.mobileaction import get
from mcp_task.services.cache import cached
from mcp_task.validation.common import (
    require_country_code,
    require_date,
    require_date_range,
    require_keyword_list,
    require_positive_int,
    require_text,
)
from mcp_task.validation.playstore import require_package_name


def fetch_keyword_ranking(track_id: str, country_code: str, keywords: str, date: str | None) -> dict:
    """Validate inputs and fetch current Google Play keyword ranking(s) for an app.

    Only cached when an explicit date is given. Without one, "current" means
    "whatever MobileAction's most recent day is" — a moving target that a
    fixed cache key can't safely represent, so that case always fetches live.
    """
    track_id = require_package_name(track_id)
    country_code = require_country_code(country_code)
    keywords = require_text(keywords, "keywords")
    if date is not None:
        date = require_date(date, "date")

    def fetch():
        return get(
            f"/playstore-keyword-ranking/{track_id}/{country_code}/keywordrankings",
            params={"keywords": keywords, "date": date},
        )

    if date is None:
        return fetch()

    cache_key = f"mcp:playstore:keyword_ranking:{track_id}:{country_code}:{keywords}:{date}"
    return cached(cache_key, fetch)


def fetch_top_keywords(track_id: str, country_code: str, date: str, limit: int | None) -> dict:
    """Validate inputs and fetch the keywords bringing a Play Store app the most search volume."""
    track_id = require_package_name(track_id)
    country_code = require_country_code(country_code)
    date = require_date(date, "date")
    limit = require_positive_int(limit, "limit")

    cache_key = f"mcp:playstore:top_keywords:{track_id}:{country_code}:{date}:{limit or 'default'}"
    return cached(
        cache_key,
        lambda: get(
            f"/playstore-keyword-ranking/{track_id}/{country_code}/top-keywords",
            params={"date": date, "limit": limit},
        ),
    )


def fetch_keyword_ranking_history(
    track_id: str,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> list:
    """Validate inputs and fetch Google Play keyword ranking history for a date range.

    Both dates are always concrete and in the past, so this is always cached.
    """
    track_id = require_package_name(track_id)
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")
    require_date_range(start_date, end_date, max_days=30)

    cache_key = f"mcp:playstore:keyword_ranking_history:{track_id}:{country_code}:{keyword}:{start_date}:{end_date}"
    return cached(
        cache_key,
        lambda: get(
            f"/playstore-keyword-ranking/{track_id}/{country_code}/{keyword}/keywordrankings",
            params={"startDate": start_date, "endDate": end_date},
        ),
    )


def fetch_keyword_ranking_history_multi(
    track_id: str,
    country_code: str,
    keywords: str,
    start_date: str,
    end_date: str,
) -> dict[str, list]:
    """Validate inputs and fetch Google Play ranking history for MULTIPLE keywords, one app.

    Returns {keyword: [day entries...]}. One MobileAction request per
    keyword — unlike the single-day ranking endpoint (fetch_keyword_ranking),
    the history endpoint only accepts one keyword per call, so this can't be
    a single batched request. Reuses fetch_keyword_ranking_history per
    keyword rather than duplicating its validation/caching, at the cost of
    re-validating track_id/country_code/date_range once per keyword (cheap —
    no extra API calls, since those are pure string checks).
    """
    track_id = require_package_name(track_id)
    country_code = require_country_code(country_code)
    require_date_range(start_date, end_date, max_days=30)
    keyword_list = require_keyword_list(keywords)

    return {
        keyword: fetch_keyword_ranking_history(track_id, country_code, keyword, start_date, end_date)
        for keyword in keyword_list
    }


def fetch_keyword_metadata(country_code: str, keyword: str) -> dict:
    """Validate inputs and fetch metadata for a single Play Store keyword."""
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")

    cache_key = f"mcp:playstore:keyword_metadata:{country_code}:{keyword}"
    return cached(
        cache_key,
        lambda: get(
            f"/playstore-keyword-ranking/{country_code}/keyword-metadata",
            params={"keyword": keyword},
        ),
    )


def fetch_apps_for_keyword(country_code: str, keyword: str) -> dict:
    """Validate inputs and fetch the Play Store apps that rank for a keyword."""
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")

    cache_key = f"mcp:playstore:apps_for_keyword:{country_code}:{keyword}"
    return cached(
        cache_key,
        lambda: get(
            f"/playstore-keyword-ranking/{country_code}/keyword-apps",
            params={"keyword": keyword},
        ),
    )


def fetch_organic_keywords(track_id: str, country_code: str, date: str, limit: int) -> dict:
    """Validate inputs and fetch the full organic keyword list for a Play Store app.

    Unlike the App Store version, there's no device split (Android has no
    iPhone/iPad equivalent), so this takes one fewer argument. limit isn't
    part of the cache key or the API call — the API always returns the full
    list, and the caller (get_playstore_organic_keywords) caps/sorts it
    client-side after this returns. Costs 50 credits per live call, so this
    is the endpoint that benefits most from caching.
    """
    track_id = require_package_name(track_id)
    country_code = require_country_code(country_code)
    date = require_date(date, "date")
    require_positive_int(limit, "limit")

    cache_key = f"mcp:playstore:organic_keywords:{track_id}:{country_code}:{date}"
    return cached(
        cache_key,
        lambda: get(
            f"/playstore-keyword-ranking/{track_id}/{country_code}/organic-keywords",
            params={"date": date},
        ),
    )


def fetch_organic_impression_share(keyword: str, country_code: str) -> dict:
    """Validate inputs and fetch a keyword's organic impression share across competing apps."""
    keyword = require_text(keyword, "keyword")
    country_code = require_country_code(country_code)

    cache_key = f"mcp:playstore:organic_impression_share:{keyword}:{country_code}"
    return cached(
        cache_key,
        lambda: get(f"/playstore-keyword-ranking/organic-impression-share/keyword/{keyword}/{country_code}"),
    )


def fetch_share_of_category(keyword: str, country_code: str) -> dict:
    """Validate inputs and fetch the category distribution a keyword appears in."""
    keyword = require_text(keyword, "keyword")
    country_code = require_country_code(country_code)

    cache_key = f"mcp:playstore:share_of_category:{keyword}:{country_code}"
    return cached(
        cache_key,
        lambda: get(f"/playstore-keyword-ranking/share-of-category/keyword/{keyword}/{country_code}"),
    )
