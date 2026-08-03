from mcp_task.clients.mobileaction import get
from mcp_task.validation import (
    require_country_code,
    require_date,
    require_date_range,
    require_device,
    require_positive_int,
    require_text,
    require_track_id,
)


def fetch_keyword_ranking(track_id: int, country_code: str, keywords: str, date: str | None) -> dict:
    """Validate inputs and fetch current keyword ranking(s) for an app."""
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    keywords = require_text(keywords, "keywords")
    if date is not None:
        date = require_date(date, "date")

    return get(
        f"/appstore-keyword-ranking/{track_id}/{country_code}/keywordrankings",
        params={"keywords": keywords, "date": date},
    )


def fetch_top_keywords(
    track_id: int, country_code: str, date: str, device: str | None, limit: int | None
) -> dict:
    """Validate inputs and fetch the keywords bringing an app the most search volume."""
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    date = require_date(date, "date")
    device = require_device(device, required=False)
    limit = require_positive_int(limit, "limit")

    return get(
        f"/appstore-keyword-ranking/{track_id}/{country_code}/top-keywords",
        params={"date": date, "device": device, "limit": limit},
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
    """
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")
    require_date_range(start_date, end_date, max_days=30)

    return get(
        f"/appstore-keyword-ranking/{track_id}/{country_code}/{keyword}/keywordrankings",
        params={"startDate": start_date, "endDate": end_date},
    )


def fetch_keyword_metadata(country_code: str, keyword: str) -> dict:
    """Validate inputs and fetch metadata for a single keyword."""
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")

    return get(
        f"/appstore-keyword-ranking/{country_code}/keyword-metadata",
        params={"keyword": keyword},
    )


def fetch_apps_for_keyword(country_code: str, keyword: str) -> dict:
    """Validate inputs and fetch the apps that rank for a keyword."""
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")

    return get(
        f"/appstore-keyword-ranking/{country_code}/keyword-apps",
        params={"keyword": keyword},
    )


def fetch_organic_keywords(track_id: int, country_code: str, device: str, date: str, limit: int) -> dict:
    """Validate inputs and fetch the full organic keyword list for an app."""
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    device = require_device(device, required=True)
    date = require_date(date, "date")
    require_positive_int(limit, "limit")

    return get(
        f"/appstore-keyword-ranking/{track_id}/{country_code}/{device}/organic-keywords",
        params={"date": date},
    )
