from mcp_task.clients.google_play_scraper import search_apps
from mcp_task.clients.mobileaction import MobileActionAPIError, get
from mcp_task.config import BATCH_LOOKUP_MAX_IDS
from mcp_task.services.cache import cached
from mcp_task.validation.common import require_country_code, require_text
from mcp_task.validation.playstore import require_package_name, require_package_name_list

# Unlike the App Store (Apple's free, authoritative iTunes API supports
# search-by-name), MobileAction has no Google Play endpoint to search by app
# name — only lookup by an already-known package id. fetch_apps_by_name below
# fills that gap with an unofficial scraper instead (see clients/
# google_play_scraper.py for why its results are candidates, not a single
# trusted answer, and why it isn't cached like the id-based lookups below).
# App details themselves change rarely, so id-based lookups are cached the
# same way keyword data is.


def fetch_app_by_track_id(track_id: str, lang_code: str = "en") -> dict:
    """Validate inputs and fetch Google Play app details by package id (or Play Store URL).

    An unrecognized package id gets a 204/empty body from MobileAction rather
    than a 404, so that case is translated into the same MobileActionAPIError
    shape a real 404 would produce elsewhere in this codebase.
    """
    track_id = require_package_name(track_id)
    lang_code = require_text(lang_code, "lang_code")

    cache_key = f"mcp:playstore:app_detail:{track_id}:{lang_code}"
    data = cached(
        cache_key,
        lambda: get(f"/playstore-appinfo-v2/app/detailed/{track_id}", params={"langCode": lang_code}),
    )

    if data is None:
        raise MobileActionAPIError(
            f"Not found: no Google Play app exists for package id '{track_id}'.", status_code=404
        )
    return data


def fetch_apps_by_name(query: str, country: str = "us", lang_code: str = "en") -> list[dict]:
    """Validate inputs and search Google Play by name for candidate matches.

    Not cached, unlike the id-based lookups above — this is a live search
    over results that shift over time, not a fixed id-keyed record. See
    clients/google_play_scraper.py for why the returned list can be missing
    the single most obvious match and should be treated as candidates.
    """
    query = require_text(query, "query")
    country = require_country_code(country, upper=False)
    lang_code = require_text(lang_code, "lang_code")
    return search_apps(query, country, lang_code)


def fetch_apps_by_track_ids(track_ids: str, lang_code: str = "en") -> tuple[list[str], list[dict]]:
    """Validate inputs and batch-look up several Google Play apps by package id.

    Returns (requested_ids, found_apps) — requested_ids is the parsed/de-duped
    id list, so the caller can report which of them MobileAction didn't find.
    """
    ids = require_package_name_list(track_ids, min_count=1, max_count=BATCH_LOOKUP_MAX_IDS)
    lang_code = require_text(lang_code, "lang_code")

    ids_param = ",".join(ids)
    cache_key = f"mcp:playstore:app_batch:{lang_code}:{ids_param}"
    apps = cached(
        cache_key,
        lambda: get(f"/playstore-appinfo-v2/app/simple/{lang_code}", params={"trackIds": ids_param}),
    )
    return ids, apps
