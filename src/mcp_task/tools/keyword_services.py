from mcp_task.clients.mobileaction import get
from mcp_task.errors import ToolError, to_error_response
from mcp_task.mcp_instance import mcp
from mcp_task.validation import (
    require_country_code,
    require_date,
    require_date_range,
    require_device,
    require_positive_int,
    require_text,
    require_track_id,
)


def _fetch_keyword_ranking(track_id: int, country_code: str, keywords: str, date: str | None) -> dict:
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


@mcp.tool
def get_keyword_ranking(
    track_id: int,
    country_code: str,
    keywords: str,
    date: str | None = None,
) -> dict:
    """Get an app's current App Store search ranking for one or more keywords.

    Returns a single day's rank (per device: iPhone/iPad) for each keyword.
    Use this when the user asks things like "what rank does app X have for
    keyword Y in country Z" or "check keyword position".

    Args:
        track_id: The app's numeric App Store id (e.g. 529479190 for Clash of Clans).
        country_code: Two-letter App Store country/storefront code, e.g. "US", "TR".
        keywords: One or more keywords, comma-separated (e.g. "ticket,event,concert").
        date: Optional date in YYYY-MM-DD format. Defaults to the most recent
            available ranking day if omitted.
    """
    try:
        data = _fetch_keyword_ranking(track_id, country_code, keywords, date)
    except ToolError as exc:
        return to_error_response(exc)

    return {"rankings": data}


def _fetch_top_keywords(
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


@mcp.tool
def get_top_keywords(
    track_id: int,
    country_code: str,
    date: str,
    device: str | None = None,
    limit: int | None = None,
) -> dict:
    """Get the keywords that bring an app the most search volume in the App Store.

    Returns a list of {keyword, searchVolume, rank} sorted by search volume,
    for a single day. Use this when the user asks things like "what keywords
    does app X get the most volume for" or "show top keywords for app X",
    as opposed to checking one specific keyword (use get_keyword_ranking for that).

    Args:
        track_id: The app's numeric App Store id (e.g. 284882215 for Facebook).
        country_code: Two-letter App Store country/storefront code, e.g. "US", "TR".
        date: Date to fetch top keywords for, in YYYY-MM-DD format (required).
        device: Optional device filter, "IPHONE" or "IPAD". Defaults to all devices.
        limit: Optional max number of keywords to return, e.g. 150.
    """
    try:
        data = _fetch_top_keywords(track_id, country_code, date, device, limit)
    except ToolError as exc:
        return to_error_response(exc)

    return {"top_keywords": data}


def fetch_keyword_ranking_history(
    track_id: int,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> list:
    """Validate inputs and fetch App Store keyword ranking history for a date range.

    Shared by both get_keyword_ranking_history and plot_keyword_ranking_history so
    they stay in sync on request shape and validation. Raises InputValidationError
    on a bad input or MobileActionAPIError on failure; returns the raw list of
    per-day, per-device {trackId, keyword, rank, countryCode, date, appKind} entries.
    """
    track_id = require_track_id(track_id)
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")
    require_date_range(start_date, end_date, max_days=30)

    return get(
        f"/appstore-keyword-ranking/{track_id}/{country_code}/{keyword}/keywordrankings",
        params={"startDate": start_date, "endDate": end_date},
    )


@mcp.tool
def get_keyword_ranking_history(
    track_id: int,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Get ONE app's App Store ranking history for a single keyword over a date range.

    Returns one rank entry per day (per device: iPhone/iPad) between start_date
    and end_date, inclusive. Use this when the user asks how a keyword's rank
    changed over time for a single app (e.g. "how has app X's rank for keyword Y
    trended over the last month"), as opposed to a single day's rank (use
    get_keyword_ranking for that).

    Do NOT call this once per app to compare multiple apps — if the user gives
    two or more apps to compare/vs/side-by-side for the same keyword (with or
    without asking for a "dashboard" or "chart"), use
    compare_keyword_ranking_history instead; it fetches every app's history
    itself in one call and renders the comparison, which this tool cannot do.
    Similarly, if the user wants a single app's trend as a chart rather than
    raw numbers, use plot_keyword_ranking_history instead.

    The date range should not exceed 30 days per request.

    Args:
        track_id: The app's numeric App Store id (e.g. 366562751 for Clash of Clans).
        country_code: Two-letter App Store country/storefront code, e.g. "US", "TR".
        keyword: A single keyword to get the ranking history for.
        start_date: History start date, inclusive, in YYYY-MM-DD format.
        end_date: History end date, inclusive, in YYYY-MM-DD format.
    """
    try:
        data = fetch_keyword_ranking_history(track_id, country_code, keyword, start_date, end_date)
    except ToolError as exc:
        return to_error_response(exc)

    return {"history": data}


def _fetch_keyword_metadata(country_code: str, keyword: str) -> dict:
    """Validate inputs and fetch metadata for a single keyword."""
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")

    return get(
        f"/appstore-keyword-ranking/{country_code}/keyword-metadata",
        params={"keyword": keyword},
    )


@mcp.tool
def get_keyword_metadata(country_code: str, keyword: str) -> dict:
    """Get metadata about a keyword in the App Store: search volume, popularity,
    detected language, how many iPhone/iPad apps target it, and its brand app.

    Use this when the user asks things like "how popular is keyword X" or
    "what's the search volume for keyword X in country Y", independent of any
    specific app.

    Args:
        country_code: Two-letter App Store country/storefront code, e.g. "US", "TR".
        keyword: A single keyword to get metadata for.
    """
    try:
        data = _fetch_keyword_metadata(country_code, keyword)
    except ToolError as exc:
        return to_error_response(exc)

    return {"metadata": data}


def _fetch_apps_for_keyword(country_code: str, keyword: str) -> dict:
    """Validate inputs and fetch the apps that rank for a keyword."""
    country_code = require_country_code(country_code)
    keyword = require_text(keyword, "keyword")

    return get(
        f"/appstore-keyword-ranking/{country_code}/keyword-apps",
        params={"keyword": keyword},
    )


@mcp.tool
def get_apps_for_keyword(country_code: str, keyword: str) -> dict:
    """Get the list of apps that rank in the App Store for a given keyword.

    This is the reverse of get_keyword_ranking / get_organic_keywords: instead
    of asking "what keywords does my app rank for", it answers "which apps
    rank for this keyword". Use this for competitor discovery or to gauge how
    competitive a keyword is (e.g. "which apps show up for 'meditation'",
    "who are my competitors for keyword X").

    Args:
        country_code: Two-letter App Store country/storefront code, e.g. "US", "TR".
        keyword: A single keyword to find ranking apps for.
    """
    try:
        data = _fetch_apps_for_keyword(country_code, keyword)
    except ToolError as exc:
        return to_error_response(exc)

    return {"apps": data}


# Large apps can organically rank for tens of thousands of keywords (e.g.
# ~36k for Duolingo), and the raw response can exceed MCP's 1MB tool-result
# limit. The API itself has no limit/pagination param for this endpoint, so
# we always fetch the full list but trim what we hand back to the model,
# sorted by best rank first, and report the true total separately.
_ORGANIC_KEYWORDS_DEFAULT_LIMIT = 1000
_ORGANIC_KEYWORDS_MAX_LIMIT = 1000


def _fetch_organic_keywords(track_id: int, country_code: str, device: str, date: str, limit: int) -> dict:
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


@mcp.tool
def get_organic_keywords(
    track_id: int,
    country_code: str,
    device: str,
    date: str,
    limit: int = _ORGANIC_KEYWORDS_DEFAULT_LIMIT,
) -> dict:
    """Get organic keywords an app ranks for in the App Store, with their ranks.

    COSTS 50 CREDITS PER REQUEST — this is significantly more expensive than
    other keyword tools, so only call it when the user specifically asks for
    the full list of organic keywords for an app (e.g. "what keywords does app
    X organically rank for"), not for single-keyword lookups (use
    get_keyword_ranking for that).

    Large apps can rank for tens of thousands of keywords, so the response is
    capped and sorted by best (lowest) rank first; check total_count in the
    response to see how many keywords exist beyond what's returned.

    Args:
        track_id: The app's numeric App Store id (e.g. 1194582243).
        country_code: Two-letter App Store country/storefront code, e.g. "US", "TR".
        device: Device type, "IPHONE" or "IPAD".
        date: Date to fetch organic keywords for, in YYYY-MM-DD format (required).
        limit: Max number of keywords to return, sorted by best rank first.
            Defaults to and is capped at 100 to avoid oversized responses.
    """
    try:
        data = _fetch_organic_keywords(track_id, country_code, device, date, limit)
    except ToolError as exc:
        return to_error_response(exc)

    rankings = data.get("rankings", [])
    capped_limit = max(1, min(limit, _ORGANIC_KEYWORDS_MAX_LIMIT))
    top_rankings = sorted(rankings, key=lambda item: item.get("rank", float("inf")))[:capped_limit]

    return {
        "track_id": data.get("trackId"),
        "country_code": data.get("countryCode"),
        "device": data.get("deviceType"),
        "date": data.get("date"),
        "total_count": len(rankings),
        "returned_count": len(top_rankings),
        "rankings": top_rankings,
    }
