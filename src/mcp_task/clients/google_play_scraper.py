import logging

from google_play_scraper import search as _search
from google_play_scraper.exceptions import NotFoundError

logger = logging.getLogger(__name__)


def search_apps(query: str, country: str, lang: str, n_hits: int = 10) -> list[dict]:
    """Search Google Play by name using the unofficial google-play-scraper package.

    Google has no official public search API, so this scrapes Play Store's
    search results page. That library has a known bug: when Google renders a
    single exact-name query as a special "top card" result, the scraper
    fails to extract that card's appId (every other field, e.g. title, comes
    through fine) — so exactly the most obvious match can be silently
    missing. Entries with no appId are dropped here rather than returned
    half-broken; callers should treat what's left as candidates to confirm,
    not a single authoritative answer.

    The library can also raise instead of returning [] for some queries with
    no results (a separate bug, not just NotFoundError) — both are treated
    as "no candidates found" here rather than crashing the caller.
    """
    try:
        results = _search(query, n_hits=n_hits, lang=lang, country=country)
    except NotFoundError:
        return []
    except (TypeError, IndexError, KeyError) as exc:
        logger.warning("google-play-scraper failed to parse results for query=%r: %s", query, exc)
        return []

    return [app for app in results if app.get("appId")]
