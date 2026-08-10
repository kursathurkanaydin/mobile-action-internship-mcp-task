import logging
from urllib.error import URLError

from google_play_scraper import search as _search
from google_play_scraper.exceptions import ExtraHTTPError, NotFoundError

from mcp_task.errors import ToolError

logger = logging.getLogger(__name__)


class PlayStoreSearchError(ToolError):
    """A clean, user-facing error for a Google Play search that failed to even run.

    Distinct from a plain empty result: NotFoundError (zero matches) returns
    [] from search_apps below, since that's a normal outcome, not a failure.
    This is raised only when the search itself couldn't complete (network
    down, Google rate-limiting/blocking the scraper) — silently returning []
    for that case would misrepresent an unknown result as "no apps found."
    """


def search_apps(query: str, country: str, lang: str, n_hits: int = 10) -> list[dict]:
    """Search Google Play by name using the unofficial google-play-scraper package.

    Google has no official public search API, so this scrapes Play Store's
    search results page (via plain urllib under the hood — no timeout is
    configured by the library, so a stalled connection can hang rather than
    fail fast; there's no hook to change that from here). That library has a
    known bug: when Google renders a single exact-name query as a special
    "top card" result, the scraper fails to extract that card's appId (every
    other field, e.g. title, comes through fine) — so exactly the most
    obvious match can be silently missing. Entries with no appId are dropped
    here rather than returned half-broken; callers should treat what's left
    as candidates to confirm, not a single authoritative answer.

    The library can also raise instead of returning [] for some queries with
    no results (a separate bug, not just NotFoundError) — both are treated
    as "no candidates found" here rather than crashing the caller. Actual
    failures (network error, Google returning a non-404 HTTP error) raise
    PlayStoreSearchError instead of masquerading as "no results."
    """
    try:
        results = _search(query, n_hits=n_hits, lang=lang, country=country)
    except NotFoundError:
        return []
    except ExtraHTTPError as exc:
        raise PlayStoreSearchError(f"Google Play search failed: {exc}", error_type="upstream_api") from exc
    except URLError as exc:
        raise PlayStoreSearchError(
            f"Network error while searching Google Play: {exc}", error_type="network"
        ) from exc
    except (TypeError, IndexError, KeyError) as exc:
        logger.warning("google-play-scraper failed to parse results for query=%r: %s", query, exc)
        return []

    return [app for app in results if app.get("appId")]
