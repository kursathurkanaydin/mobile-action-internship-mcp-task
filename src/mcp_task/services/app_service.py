from mcp_task.clients.itunes import lookup_app, lookup_apps, search_app
from mcp_task.validation import require_country_code, require_text, require_track_id, require_track_id_list

# iTunes' lookup endpoint comfortably supports a couple hundred comma-joined
# ids per request; this stays well under that so a single batch call never
# risks a rejected/oversized request.
_BATCH_LOOKUP_MAX_IDS = 150


def fetch_app_by_name(app_name: str, country: str) -> dict:
    """Validate inputs and look up an app on the App Store by name."""
    app_name = require_text(app_name, "app_name")
    country = require_country_code(country, upper=False)
    return search_app(app_name, country)


def fetch_app_by_track_id(track_id: int, country: str) -> dict:
    """Validate inputs and look up an app on the App Store by trackId."""
    track_id = require_track_id(track_id)
    country = require_country_code(country, upper=False)
    return lookup_app(track_id, country)


def fetch_apps_by_track_ids(track_ids: str, country: str) -> tuple[list[int], list[dict]]:
    """Validate inputs and batch-look up several apps on the App Store by trackId.

    Returns (requested_ids, found_apps) — requested_ids is the parsed/de-duped
    id list, so the caller can report which of them iTunes didn't find (it
    silently omits unknown ids rather than erroring).
    """
    ids = require_track_id_list(track_ids, min_count=1, max_count=_BATCH_LOOKUP_MAX_IDS)
    country = require_country_code(country, upper=False)
    return ids, lookup_apps(ids, country)
