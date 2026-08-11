from mcp_task.clients.mobileaction import get
from mcp_task.services.cache import cached
from mcp_task.validation.common import require_text
from mcp_task.validation.other import require_store


def fetch_app_match(store: str, track_id: str) -> str | None:
    """Validate inputs and fetch the given app's id in the OPPOSITE store.

    store identifies which store track_id belongs to ("ios" or "play"); the
    response is the same app's id on the other store. Unlike every other
    MobileAction endpoint this project calls, app-match replies with a bare
    text/plain body (e.g. "com.facebook.katana"), not JSON - hence get(...,
    raw=True). An app's counterpart is stable metadata, not time-sensitive
    data, so this is always cached.
    """
    store = require_store(store)
    track_id = require_text(track_id, "track_id")

    cache_key = f"mcp:other:app_match:{store}:{track_id}"
    return cached(cache_key, lambda: get(f"/app-match/app/{store}", params={"trackId": track_id}, raw=True))
