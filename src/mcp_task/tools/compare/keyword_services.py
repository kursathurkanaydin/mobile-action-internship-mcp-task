from mcp_task.errors import handle_tool_errors
from mcp_task.mcp_instance import mcp
from mcp_task.services.compare.keyword_service import (
    fetch_keyword_metadata,
    fetch_keyword_ranking,
    fetch_keyword_ranking_history,
    fetch_top_keywords,
)


@mcp.tool
@handle_tool_errors
def compare_stores_keyword_metadata(country_code: str, keyword: str) -> dict:
    """Compare a keyword's search volume/popularity between the App Store and Google Play.

    Keyword metadata is app-independent, so this needs no app id from either
    store — just the keyword text and country. Use this when the user asks
    something like "is 'meditation' searched more on iOS or Android" or
    "compare keyword X between the two stores", without reference to a
    specific app's ranking.

    Args:
        country_code: Two-letter storefront code, used for both stores, e.g. "US", "TR".
        keyword: A single keyword to compare metadata for.
    """
    data = fetch_keyword_metadata(country_code, keyword)
    return {"app_store": {"metadata": data["app_store"]}, "play_store": {"metadata": data["play_store"]}}


@mcp.tool
@handle_tool_errors
def compare_stores_keyword_ranking(
    app_store_track_id: int,
    playstore_track_id: str,
    country_code: str,
    keywords: str,
    date: str | None = None,
) -> dict:
    """Compare one app's current App Store vs Google Play ranking for one or more keywords.

    Needs the SAME app's id on both stores — there's no automatic mapping
    between an App Store trackId and a Play Store package id, so both must
    be given explicitly. If you only have a name, resolve it first with
    get_app_store_id (App Store, authoritative search) and
    get_playstore_app_id/get_playstore_app_name (Play Store — no real
    search exists, see get_playstore_app_id's docstring). This is a
    single-day snapshot; for a trend over time use
    compare_stores_keyword_ranking_history instead, or
    plot_compare_stores_keyword_ranking if the request wants a chart.

    Args:
        app_store_track_id: The app's numeric App Store id (e.g. 529479190 for Clash of Clans).
        playstore_track_id: The SAME app's Google Play package id (e.g. "com.supercell.clashofclans").
        country_code: Two-letter storefront code, used for both stores, e.g. "US", "TR".
        keywords: One or more keywords, comma-separated (e.g. "clan,war").
        date: Optional date in YYYY-MM-DD format. Defaults to the most recent
            available ranking day on each store if omitted.
    """
    data = fetch_keyword_ranking(app_store_track_id, playstore_track_id, country_code, keywords, date)
    return {"app_store": {"rankings": data["app_store"]}, "play_store": {"rankings": data["play_store"]}}


@mcp.tool
@handle_tool_errors
def compare_stores_keyword_ranking_history(
    app_store_track_id: int,
    playstore_track_id: str,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Compare one app's App Store vs Google Play ranking history for one keyword over a date range.

    Needs the SAME app's id on both stores (see compare_stores_keyword_ranking for
    how to resolve them). Returns raw per-day data for each store — no
    chart. If the user wants to *see* the trend, use
    plot_compare_stores_keyword_ranking_history instead. The date range should not
    exceed 30 days per request.

    Args:
        app_store_track_id: The app's numeric App Store id (e.g. 529479190 for Clash of Clans).
        playstore_track_id: The SAME app's Google Play package id (e.g. "com.supercell.clashofclans").
        country_code: Two-letter storefront code, used for both stores, e.g. "US", "TR".
        keyword: A single keyword to compare ranking history for.
        start_date: History start date, inclusive, in YYYY-MM-DD format.
        end_date: History end date, inclusive, in YYYY-MM-DD format.
    """
    data = fetch_keyword_ranking_history(
        app_store_track_id, playstore_track_id, country_code, keyword, start_date, end_date
    )
    return {"app_store": {"history": data["app_store"]}, "play_store": {"history": data["play_store"]}}


@mcp.tool
@handle_tool_errors
def compare_stores_top_keywords(
    app_store_track_id: int,
    playstore_track_id: str,
    country_code: str,
    date: str,
    device: str | None = None,
    limit: int | None = None,
) -> dict:
    """Compare the keywords bringing one app the most search volume on the App Store vs Google Play.

    Needs the SAME app's id on both stores (see compare_stores_keyword_ranking for
    how to resolve them). The two stores' top-keyword lists are independent
    — a keyword topping one store's list may not even appear on the
    other's — so this returns both lists side by side rather than trying to
    force a 1:1 match.

    Args:
        app_store_track_id: The app's numeric App Store id (e.g. 529479190 for Clash of Clans).
        playstore_track_id: The SAME app's Google Play package id (e.g. "com.supercell.clashofclans").
        country_code: Two-letter storefront code, used for both stores, e.g. "US", "TR".
        date: Date to fetch top keywords for, in YYYY-MM-DD format (required).
        device: Optional App Store device filter, "IPHONE" or "IPAD" — has no
            effect on the Play Store side (Android has no device split).
        limit: Optional max number of keywords to return, per store.
    """
    data = fetch_top_keywords(app_store_track_id, playstore_track_id, country_code, date, device, limit)
    return {"app_store": {"top_keywords": data["app_store"]}, "play_store": {"top_keywords": data["play_store"]}}
