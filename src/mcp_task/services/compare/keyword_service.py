from mcp_task.services.appstore import keyword_service as appstore_keyword_service
from mcp_task.services.playstore import keyword_service as playstore_keyword_service

# Needs a real id from each store — there's no automatic way to map an App
# Store trackId to its Play Store package id (or vice versa), so callers
# always supply both explicitly. Validation happens inside each store's own
# fetch_* function (require_track_id vs require_package_name), so it isn't
# repeated here.


def fetch_keyword_metadata(country_code: str, keyword: str) -> dict:
    """Fetch keyword metadata from both stores for the same keyword+country, for side-by-side comparison.

    Keyword metadata is app-independent (search volume/popularity for the
    keyword itself), so unlike the other fetch_* functions here this needs
    no app id from either store.
    """
    return {
        "app_store": appstore_keyword_service.fetch_keyword_metadata(country_code, keyword),
        "play_store": playstore_keyword_service.fetch_keyword_metadata(country_code, keyword),
    }


def fetch_keyword_ranking(
    app_store_track_id: int,
    playstore_track_id: str,
    country_code: str,
    keywords: str,
    date: str | None = None,
) -> dict:
    """Fetch current keyword ranking(s) from both stores for the same app pair."""
    return {
        "app_store": appstore_keyword_service.fetch_keyword_ranking(app_store_track_id, country_code, keywords, date),
        "play_store": playstore_keyword_service.fetch_keyword_ranking(
            playstore_track_id, country_code, keywords, date
        ),
    }


def fetch_keyword_ranking_history(
    app_store_track_id: int,
    playstore_track_id: str,
    country_code: str,
    keyword: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Fetch keyword ranking history from both stores for the same app pair."""
    return {
        "app_store": appstore_keyword_service.fetch_keyword_ranking_history(
            app_store_track_id, country_code, keyword, start_date, end_date
        ),
        "play_store": playstore_keyword_service.fetch_keyword_ranking_history(
            playstore_track_id, country_code, keyword, start_date, end_date
        ),
    }


def fetch_top_keywords(
    app_store_track_id: int,
    playstore_track_id: str,
    country_code: str,
    date: str,
    device: str | None = None,
    limit: int | None = None,
) -> dict:
    """Fetch the keywords bringing the most search volume from both stores, for the same app pair.

    device only affects the App Store side — Play Store has no device split,
    so it's ignored there; defaults to None either way.
    """
    return {
        "app_store": appstore_keyword_service.fetch_top_keywords(
            app_store_track_id, country_code, date, device, limit
        ),
        "play_store": playstore_keyword_service.fetch_top_keywords(playstore_track_id, country_code, date, limit),
    }
