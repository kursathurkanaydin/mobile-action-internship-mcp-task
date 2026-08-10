from mcp_task.errors import handle_tool_errors
from mcp_task.mcp_instance import mcp
from mcp_task.services.playstore.keyword_service import (
    fetch_apps_for_keyword,
    fetch_keyword_metadata,
    fetch_keyword_ranking,
    fetch_keyword_ranking_history,
    fetch_keyword_ranking_history_multi,
    fetch_organic_impression_share,
    fetch_organic_keywords,
    fetch_share_of_category,
    fetch_top_keywords,
)

# Same rationale as get_organic_keywords in tools/appstore/keyword_services.py: large
# apps can organically rank for tens of thousands of keywords, which can
# exceed MCP's 1MB tool-result limit, so the response is always capped and
# sorted by best rank first.
_ORGANIC_KEYWORDS_DEFAULT_LIMIT = 1000
_ORGANIC_KEYWORDS_MAX_LIMIT = 1000


@mcp.tool
@handle_tool_errors
def get_playstore_keyword_ranking(
    track_id: str,
    country_code: str,
    keywords: str,
    date: str | None = None,
) -> dict:
    """Get an app's current Google Play Store search ranking for one or more keywords.

    Returns a single day's rank for each keyword. Use this when the user asks
    things like "what rank does app X have for keyword Y in country Z" on
    Google Play, as opposed to a trend over time (use
    get_playstore_keyword_ranking_history for that).

    Args:
        track_id: The app's Google Play package name (e.g. "com.facebook.katana").
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
        keywords: One or more keywords, comma-separated (e.g. "ticket,event,concert").
        date: Optional date in YYYY-MM-DD format. Defaults to the most recent
            available ranking day if omitted.
    """
    data = fetch_keyword_ranking(track_id, country_code, keywords, date)
    return {"rankings": data}


@mcp.tool
@handle_tool_errors
def get_playstore_top_keywords(
    track_id: str,
    country_code: str,
    date: str,
    limit: int | None = None,
) -> dict:
    """Get the keywords that bring an app the most search volume on Google Play.

    Returns a list of {keyword, searchVolume, rank} sorted by search volume,
    for a single day.

    Args:
        track_id: The app's Google Play package name (e.g. "com.facebook.katana").
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
        date: Date to fetch top keywords for, in YYYY-MM-DD format (required).
        limit: Optional max number of keywords to return.
    """
    data = fetch_top_keywords(track_id, country_code, date, limit)
    return {"top_keywords": data}


@mcp.tool
@handle_tool_errors
def get_playstore_keyword_ranking_history(
    track_id: str,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Get one app's RAW Google Play ranking history for a single keyword over a date range.

    Returns one rank entry per day between start_date and end_date, inclusive,
    as plain data — no chart, no image, no URL. The date range should not
    exceed 30 days per request.

    Args:
        track_id: The app's Google Play package name (e.g. "com.facebook.katana").
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
        keyword: A single keyword to get the ranking history for.
        start_date: History start date, inclusive, in YYYY-MM-DD format.
        end_date: History end date, inclusive, in YYYY-MM-DD format.
    """
    data = fetch_keyword_ranking_history(track_id, country_code, keyword, start_date, end_date)
    return {"history": data}


@mcp.tool
@handle_tool_errors
def get_playstore_keyword_ranking_history_multi(
    track_id: str,
    country_code: str,
    keywords: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Get one app's RAW Google Play ranking history for MULTIPLE keywords over a date range.

    Same as get_playstore_keyword_ranking_history, but for two or more
    keywords at once — e.g. "how has app X ranked for 'game', 'strategy',
    'clan', and 'war' over the last 30 days on Google Play" (as opposed to
    one keyword, which is get_playstore_keyword_ranking_history's job).
    Returns one rank entry per day, per keyword, as plain data — no chart.

    Call this ONCE with all the keywords comma-separated — do not call
    get_playstore_keyword_ranking_history once per keyword and combine the
    results yourself; each keyword still costs a separate MobileAction
    request (the history endpoint has no batch-keyword mode), but this tool
    does that fetching itself in one call, which
    plot_playstore_keyword_ranking_history_multi also relies on to draw the
    chart. The date range should not exceed 30 days per request; up to 10
    keywords are supported.

    Args:
        track_id: The app's Google Play package name (e.g. "com.supercell.clashofclans").
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
        keywords: Two or more keywords, comma-separated (e.g. "game,strategy,clan,war").
        start_date: History start date, inclusive, in YYYY-MM-DD format.
        end_date: History end date, inclusive, in YYYY-MM-DD format.
    """
    data = fetch_keyword_ranking_history_multi(track_id, country_code, keywords, start_date, end_date)
    return {"history_by_keyword": data}


@mcp.tool
@handle_tool_errors
def get_playstore_keyword_metadata(country_code: str, keyword: str) -> dict:
    """Get metadata about a keyword on Google Play: search volume, popularity,
    and how many apps target it.

    Use this when the user asks things like "how popular is keyword X on
    Google Play", independent of any specific app.

    Args:
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
        keyword: A single keyword to get metadata for.
    """
    data = fetch_keyword_metadata(country_code, keyword)
    return {"metadata": data}


@mcp.tool
@handle_tool_errors
def get_playstore_apps_for_keyword(country_code: str, keyword: str) -> dict:
    """Get the list of apps that rank on Google Play for a given keyword.

    This is the reverse of get_playstore_keyword_ranking /
    get_playstore_organic_keywords: instead of asking "what keywords does my
    app rank for", it answers "which apps rank for this keyword". Use this for
    competitor discovery on Google Play.

    Args:
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
        keyword: A single keyword to find ranking apps for.
    """
    data = fetch_apps_for_keyword(country_code, keyword)
    return {"apps": data}


@mcp.tool
@handle_tool_errors
def get_playstore_organic_keywords(
    track_id: str,
    country_code: str,
    date: str,
    limit: int = _ORGANIC_KEYWORDS_DEFAULT_LIMIT,
) -> dict:
    """Get organic keywords an app ranks for on Google Play, with their ranks.

    COSTS 50 CREDITS PER REQUEST — this is significantly more expensive than
    other keyword tools, so only call it when the user specifically asks for
    the full list of organic keywords for an app, not for single-keyword
    lookups (use get_playstore_keyword_ranking for that).

    Large apps can rank for tens of thousands of keywords, so the response is
    capped and sorted by best (lowest) rank first; check total_count in the
    response to see how many keywords exist beyond what's returned.

    Args:
        track_id: The app's Google Play package name (e.g. "com.duolingo").
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
        date: Date to fetch organic keywords for, in YYYY-MM-DD format (required).
        limit: Max number of keywords to return, sorted by best rank first.
            Defaults to and is capped at 1000 to avoid oversized responses.
    """
    data = fetch_organic_keywords(track_id, country_code, date, limit)

    rankings = data.get("rankings", [])
    capped_limit = max(1, min(limit, _ORGANIC_KEYWORDS_MAX_LIMIT))
    top_rankings = sorted(rankings, key=lambda item: item.get("rank", float("inf")))[:capped_limit]

    return {
        "track_id": data.get("trackId"),
        "country_code": data.get("countryCode"),
        "date": data.get("date"),
        "total_count": len(rankings),
        "returned_count": len(top_rankings),
        "rankings": top_rankings,
    }


@mcp.tool
@handle_tool_errors
def get_playstore_organic_impression_share(keyword: str, country_code: str) -> dict:
    """Get a keyword's organic impression share distribution across competing apps on Google Play.

    Use this when the user asks how visibility for a keyword is split between
    the apps that rank for it — "who's dominating impressions for keyword X".

    Args:
        keyword: A single keyword to get impression share for.
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
    """
    data = fetch_organic_impression_share(keyword, country_code)
    return {"impression_share": data}


@mcp.tool
@handle_tool_errors
def get_playstore_share_of_category(keyword: str, country_code: str) -> dict:
    """Get the category distribution a keyword appears in on Google Play.

    Use this when the user asks what app categories a keyword is associated
    with, e.g. "what category does keyword X belong to".

    Args:
        keyword: A single keyword to get category distribution for.
        country_code: Two-letter Play Store country code, e.g. "US", "TR".
    """
    data = fetch_share_of_category(keyword, country_code)
    return {"share_of_category": data}
