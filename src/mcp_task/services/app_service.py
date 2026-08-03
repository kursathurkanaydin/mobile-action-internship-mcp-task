from mcp_task.clients.itunes import lookup_app, search_app
from mcp_task.validation import require_country_code, require_text, require_track_id


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
