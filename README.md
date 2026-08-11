# MobileAction MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes MobileAction's
**Keyword Services** API — for both the **App Store** and **Google Play
Store** — as tools an LLM (Claude Desktop, Cursor, MCP Inspector, etc.) can
call directly. Ask something like *"What keywords does Duolingo rank best for
on the US App Store?"* or *"What's Duolingo's organic impression share for
'language learning' on Google Play?"* and the model resolves the app, calls
the right tool, and answers from real MobileAction data.

## Why Python + FastMCP

Python has the most mature official MCP SDK, and [FastMCP](https://gofastmcp.com)
builds on it to turn a plain decorated function (`@mcp.tool`) into a fully
schema'd MCP tool — parameter types, docstrings, and validation all come from
ordinary Python, with no protocol boilerplate to hand-write. Given the goal is
"correctly expose a handful of REST endpoints as tools," this let the effort
go into tool design, validation, and error handling rather than into wiring up
JSON-RPC by hand.

## Tools

Credit costs below are the real `X-Credit-Cost` response header measured
against the live API (one call per endpoint) — not estimates. They're flat
per call, not per keyword (e.g. `get_appstore_keyword_ranking` costs 3 credits whether
you pass one keyword or four). Every tool's actual response also carries its
own `credit_cost`/`credit_remaining` live, not just this static table — see
[Credit awareness](#credit-awareness).

**Account**
| Tool | Description | Credits/call |
|---|---|---|
| `get_remaining_api_credits` | Check the MobileAction API key's credit balance. | Free |

**App Store Keyword Services** (MobileAction `/appstore-keyword-ranking/*`)
| Tool | Description | Credits/call |
|---|---|---|
| `get_appstore_keyword_ranking` | Current rank for one or more keywords, one day. **Redis-cached for 24h** when a `date` is given (bonus) — an undated "most recent" query always fetches live. | 3, 0 on a cache hit |
| `get_appstore_apps_for_keyword` | Which apps rank for a given keyword (competitor discovery). **Redis-cached for 24h** (bonus). | 5, 0 on a cache hit |
| `get_appstore_keyword_metadata` | Search volume/popularity for a keyword, independent of any app. **Redis-cached for 24h** (bonus). | 5, 0 on a cache hit |
| `get_appstore_keyword_ranking_history` | Rank history for one keyword for an app over a date range. **Redis-cached for 24h** (bonus). | 10, 0 on a cache hit |
| `get_appstore_top_keywords` | Keywords bringing an app the most search volume. **Redis-cached for 24h** (bonus). | 20, 0 on a cache hit |
| `get_appstore_organic_keywords` | Full list of keywords an app organically ranks for. **Redis-cached for 24h** (bonus). | **50**, 0 on a cache hit |

**Google Play Store Keyword Services** (MobileAction `/playstore-keyword-ranking/*`) —
same shape as App Store above, except `track_id` is the app's package name
(e.g. `com.facebook.katana`) instead of a numeric id, and there's no
device (iPhone/iPad) split since Android has none. All Redis-cached for 24h
the same way.
| Tool | Description | Credits/call |
|---|---|---|
| `get_playstore_keyword_ranking` | Current rank for one or more keywords, one day. | 3, 0 on a cache hit |
| `get_playstore_apps_for_keyword` | Which apps rank for a given keyword. | 5, 0 on a cache hit |
| `get_playstore_keyword_metadata` | Search volume/popularity for a keyword. | 5, 0 on a cache hit |
| `get_playstore_share_of_category` | Which app categories a keyword's search results fall into. | 5, 0 on a cache hit |
| `get_playstore_keyword_ranking_history` | Rank history for one keyword for an app over a date range. | 10, 0 on a cache hit |
| `get_playstore_keyword_ranking_history_multi` | Rank history for one or more keywords for one app over a date range, in one call. | 10 × number of keywords (one history call per keyword) |
| `get_playstore_organic_impression_share` | Impression share for a keyword split across the apps competing for it. | 20, 0 on a cache hit |
| `get_playstore_top_keywords` | Keywords bringing an app the most search volume. | 20, 0 on a cache hit |
| `get_playstore_organic_keywords` | Full list of keywords an app organically ranks for. | **50**, 0 on a cache hit |

**App Store lookup** (helper — calls Apple's free iTunes API, not MobileAction, since
MobileAction's endpoints need a numeric `trackId` rather than an app name)
| Tool | Description | Credits/call |
|---|---|---|
| `get_appstore_id` | Resolve an app name to its numeric App Store id. | Free (external API) |
| `get_appstore_name` | Resolve a numeric App Store id back to its name. | Free (external API) |
| `get_appstore_names_batch` | Resolve 1–300 numeric App Store ids to names in one request (limit configurable via `BATCH_LOOKUP_MAX_IDS`; e.g. the competitor trackIds from `get_appstore_apps_for_keyword`) instead of one call per id. | Free (external API) |

**Google Play lookup** — unlike the App Store, Google has no free public
search API and MobileAction has no name→id search endpoint either (confirmed
in their docs). `get_playstore_app_name`/`_batch` accept either a bare
package id (`com.facebook.katana`) or a full Play Store URL (e.g. the one you
get from sharing an app, `https://play.google.com/store/apps/details?id=com.facebook.katana`)
— the id is extracted automatically — and are **Redis-cached for 24h**, same
as the keyword tools, since app details rarely change.

`get_playstore_app_id` fills the search-by-name gap using the **unofficial**
[`google-play-scraper`](https://pypi.org/project/google-play-scraper/) package
(scrapes Play Store's search page — there's no official API to call instead).
It's free but **not authoritative like `get_appstore_id`**: a known bug in
that library drops the id for Google's special "top card" result on an
exact-name match, so the single most obvious app can be missing from the
results. Treat its output as candidates to confirm with `get_playstore_app_name`,
not a trusted single answer. Not cached, since it's a live search.
| Tool | Description | Credits/call |
|---|---|---|
| `get_playstore_app_id` | Search Google Play by name for candidate package ids. **Unofficial/best-effort** (see above). | Free (unofficial scraper) |
| `get_playstore_app_name` | Resolve a Google Play package id or Play Store URL to the app's name/details. Internally a single-id call to the same endpoint `_batch` uses (the pricier "detailed" endpoint's extra fields — full description, screenshots, rating breakdown — aren't used here). | 1, 0 on a cache hit |
| `get_playstore_app_names_batch` | Resolve multiple package ids to names in one request (flat cost regardless of count). | 1, 0 on a cache hit |

**Cross-store comparison** (bonus — needs the SAME app's id on both stores;
there's no automatic mapping between an App Store trackId and a Play Store
package id, so both are always required explicitly). Cost is the sum of both
stores' underlying calls.
| Tool | Description | Credits/call |
|---|---|---|
| `compare_stores_keyword_metadata` | Search volume/popularity for a keyword on both stores. App-independent — no app id needed. | 5 + 5, 0 per side on a cache hit |
| `compare_stores_keyword_ranking` | Current rank for one or more keywords on both stores, one day. | 3 + 3, 0 per side on a cache hit |
| `compare_stores_keyword_ranking_history` | Rank history for one keyword on both stores over a date range. | 10 + 10, 0 per side on a cache hit |
| `compare_stores_top_keywords` | Keywords bringing the app the most search volume on each store — the two lists are independent, shown side by side. | 20 + 20, 0 per side on a cache hit |

**Interactive charts** (bonus — render the keyword data above as a
self-contained HTML page with a live Chart.js chart, instead of raw JSON).
Cost is just the underlying MobileAction call(s) they wrap — no extra charge
for rendering.
| Tool | Description | Credits/call |
|---|---|---|
| `plot_appstore_keyword_ranking` | Bar chart of one app's rank across several keywords. | 3 (same as `get_appstore_keyword_ranking`) |
| `plot_appstore_keyword_ranking_history` | Line chart of one app's rank over time. | 10 (same as `get_appstore_keyword_ranking_history`) |
| `compare_appstore_keyword_ranking_history` | Line chart comparing 2–5 apps' rank over time, same store. | 10 × number of apps (one history call per app) |
| `plot_playstore_keyword_ranking_history` | Line chart of one Google Play app's rank over time, one keyword. No device toggle (Play Store has no iPhone/iPad split). | 10 (same as `get_playstore_keyword_ranking_history`) |
| `plot_playstore_keyword_ranking_history_multi` | Line chart comparing one Google Play app's rank across 2–10 keywords over time. No device toggle (Play Store has no iPhone/iPad split). | 10 × number of keywords (one history call per keyword) |
| `plot_compare_stores_keyword_ranking` | Grouped bar chart comparing one app's App Store vs Play Store rank, per keyword, one day. | 3 + 3 (same as `compare_stores_keyword_ranking`) |
| `plot_compare_stores_keyword_ranking_history` | Line chart comparing one app's App Store vs Play Store rank over time, one keyword. App Store's iPhone/iPad ranks are pre-merged — no device toggle. | 10 + 10 (same as `compare_stores_keyword_ranking_history`) |

### Example requests

What each tool actually calls under the hood (`529479190` = Clash of Clans'
trackId, `US` storefront, keyword `strategy`). The two chart tools that plot
a single app/keyword (`plot_appstore_keyword_ranking`, `plot_appstore_keyword_ranking_history`)
hit the exact same endpoints as `get_appstore_keyword_ranking` /
`get_appstore_keyword_ranking_history` below — they just render the response as a
chart instead of returning it raw; `compare_appstore_keyword_ranking_history` calls
the `get_appstore_keyword_ranking_history` endpoint once per app being compared.

```
get_remaining_api_credits
  GET https://api.mobileaction.co/api-key?token=YOUR_API_KEY

get_appstore_keyword_ranking
  GET https://api.mobileaction.co/appstore-keyword-ranking/529479190/US/keywordrankings
      ?keywords=strategy&token=YOUR_MOBILEACTION_API_KEY

get_appstore_top_keywords
  GET https://api.mobileaction.co/appstore-keyword-ranking/529479190/US/top-keywords
      ?date=2026-07-01&token=YOUR_MOBILEACTION_API_KEY

get_appstore_keyword_ranking_history
  GET https://api.mobileaction.co/appstore-keyword-ranking/529479190/US/strategy/keywordrankings
      ?startDate=2026-07-01&endDate=2026-07-15&token=YOUR_MOBILEACTION_API_KEY

get_appstore_keyword_metadata
  GET https://api.mobileaction.co/appstore-keyword-ranking/US/keyword-metadata
      ?keyword=strategy&token=YOUR_MOBILEACTION_API_KEY

get_appstore_apps_for_keyword
  GET https://api.mobileaction.co/appstore-keyword-ranking/US/keyword-apps
      ?keyword=strategy&token=YOUR_MOBILEACTION_API_KEY

get_appstore_organic_keywords
  GET https://api.mobileaction.co/appstore-keyword-ranking/529479190/US/IPHONE/organic-keywords
      ?date=2026-07-01&token=YOUR_MOBILEACTION_API_KEY

get_appstore_id                                 (Apple's iTunes API, not MobileAction)
  GET https://itunes.apple.com/search?term=Clash+of+Clans&entity=software&country=us&limit=1

get_appstore_name                                     (Apple's iTunes API, not MobileAction)
  GET https://itunes.apple.com/lookup?id=529479190&country=us

get_appstore_names_batch                              (Apple's iTunes API, not MobileAction)
  GET https://itunes.apple.com/lookup?id=570060128,389801252,284882215&country=us
```

Google Play Store tools follow the same pattern under `/playstore-keyword-ranking/*`,
using a package name instead of a numeric trackId (`com.duolingo` below):

```
get_playstore_keyword_ranking
  GET https://api.mobileaction.co/playstore-keyword-ranking/com.duolingo/US/keywordrankings
      ?keywords=language+learning&token=YOUR_MOBILEACTION_API_KEY

get_playstore_keyword_ranking_history            (and plot_playstore_keyword_ranking_history — same call)
  GET https://api.mobileaction.co/playstore-keyword-ranking/com.supercell.clashofclans/TR/strateji/keywordrankings
      ?startDate=2026-07-12&endDate=2026-08-10&token=YOUR_MOBILEACTION_API_KEY

get_playstore_keyword_ranking_history_multi      (and plot_playstore_keyword_ranking_history_multi — same call, once per keyword)
  GET https://api.mobileaction.co/playstore-keyword-ranking/com.supercell.clashofclans/TR/oyun/keywordrankings
      ?startDate=2026-07-12&endDate=2026-08-10&token=YOUR_MOBILEACTION_API_KEY
  GET https://api.mobileaction.co/playstore-keyword-ranking/com.supercell.clashofclans/TR/strateji/keywordrankings
      ?startDate=2026-07-12&endDate=2026-08-10&token=YOUR_MOBILEACTION_API_KEY
  ... (one request per keyword; "klan", "savas" follow the same pattern)

get_playstore_organic_impression_share
  GET https://api.mobileaction.co/playstore-keyword-ranking/organic-impression-share/keyword/meditation/US
      ?token=YOUR_MOBILEACTION_API_KEY

get_playstore_share_of_category
  GET https://api.mobileaction.co/playstore-keyword-ranking/share-of-category/keyword/meditation/US
      ?token=YOUR_MOBILEACTION_API_KEY

get_playstore_app_id                             (unofficial google-play-scraper, not MobileAction or Google)
  scrapes https://play.google.com/store/search?q=WhatsApp&c=apps&hl=en&gl=us

get_playstore_app_name                           (MobileAction, unlike the free iTunes lookup above — same endpoint as _batch, just one id)
  GET https://api.mobileaction.co/playstore-appinfo-v2/app/simple/en
      ?trackIds=com.duolingo&token=YOUR_MOBILEACTION_API_KEY

get_playstore_app_names_batch                    (MobileAction, unlike the free iTunes lookup above)
  GET https://api.mobileaction.co/playstore-appinfo-v2/app/simple/en
      ?trackIds=com.duolingo,com.facebook.katana&token=YOUR_MOBILEACTION_API_KEY
```

`compare_stores_*` / `plot_compare_stores_*` tools call the matching App
Store and Play Store endpoints above once each, in one call — e.g.
`compare_stores_keyword_ranking(529479190, "com.supercell.clashofclans", "US", "clan")`
hits the exact same two `get_appstore_keyword_ranking` / `get_playstore_keyword_ranking`
URLs shown earlier, combined under `{"app_store": ..., "play_store": ...}`.

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <this-repo-url>
cd mcp-task
uv sync
```

Add your MobileAction API key — copy `.env.example` to `.env` and fill it in:

```bash
cp .env.example .env
# then edit .env:
# MOBILEACTION_API_KEY=your-real-key-here
```

The key is read from this environment variable at startup (`src/mcp_task/config.py`);
it is never hardcoded, and `.env` is gitignored.

**Redis (optional):** the endpoints marked "Redis-cached" above cache their
response for 24h behind a `REDIS_URL` env var (defaults to
`redis://localhost:6379/0`). Redis isn't required to run the server — if it's
unreachable, every cached tool just falls back to a live API call.

## Running it standalone (sanity check)

```bash
uv run src/mcp_task/server.py
```

This starts listening on stdio. Press
`Ctrl+C` to stop — this mode is just to confirm the server boots and your API
key is picked up; a real client (below) is how you actually use it.

## Connecting with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run src/mcp_task/server.py
```

This opens a browser UI listing every tool, where you can fill in parameters
and call each one manually against the real API.

## Connecting with Claude Desktop

Add this to Claude Desktop's config
(`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "mobileaction": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/mcp_task", "run", "src/mcp_task/server.py"]
    }
  }
}
```

Restart Claude Desktop, then ask it something like *"What's my MobileAction
credit balance?"* or *"Show me the top keywords for Duolingo on the US App
Store for 2026-07-01."*

## Example prompts

More prompts to try once connected, one per tool, split by store (Turkish
versions in the matching `example_prompts.txt` file):

**App Store** ([`tools/appstore/example_prompts.txt`](src/mcp_task/tools/appstore/example_prompts.txt))

- Credit check: *"How many credits do I have left on my MobileAction API key?"*
- App search: *"Find Clash of Clans' App Store id."*
- App name lookup: *"What app has track id 570060128?"*
- Batch app name lookup: *"Can you show me the names of the apps with track ids 570060128, 389801252, and 284882215?"*
- Keyword ranking: *"What's Clash of Clans' current ranking for the keyword 'strategy' on the US App Store?"*
- Top keywords: *"Show me the keywords that bring Facebook the most search volume on the US App Store for 2026-07-01."*
- Ranking history: *"How has Clash of Clans' ranking for the keyword 'strategy game' changed over the last 30 days on the US App Store?"*
- Keyword metadata: *"What's the search volume and popularity of the keyword 'meditation' on the US App Store?"*
- Competitor/app lookup: *"Which apps rank for the keyword 'meditation' on the US App Store?"*
- Batch-resolve competitor names: *"Can you also show me the names of the apps that rank for 'meditation' on the US App Store?"*
- Organic keywords (costs 50 credits, test carefully): *"Show me the keywords Duolingo organically ranks for on iPhone, for the date 2026-07-01."*
- Compare history: *"Can you compare Clash of Clans and Clash Royale's ranking history for the keyword 'strategy game' on the US App Store over the last 15 days?"*
- Keyword ranking chart: *"Can you chart Clash of Clans' ranking for the keywords 'clan', 'clash', 'war', and 'strategy' on the US App Store?"*
- Ranking history chart: *"Can you show me a chart of how Clash of Clans' ranking for the keyword 'strategy game' has changed over the last 30 days on the US App Store?"*

**Google Play** ([`tools/playstore/example_prompts.txt`](src/mcp_task/tools/playstore/example_prompts.txt))

- Search by name for a package id (unofficial/best-effort): *"Can you find Spotify's Play Store package id?"*
- App lookup by package id: *"What app has the package id com.duolingo?"*
- App lookup from a Play Store URL: *"What app is this? https://play.google.com/store/apps/details?id=com.block.juggle"*
- Batch app name lookup: *"Can you show me the names of the apps with package ids com.duolingo and com.block.juggle?"*
- Keyword ranking: *"What rank does com.duolingo have for the keyword 'language learning' on the US Play Store?"*
- Top keywords: *"Show me the keywords that bring com.duolingo the most search volume on the US Play Store for 2026-07-01."*
- Ranking history: *"How has com.duolingo's ranking for the keyword 'language learning' changed over the last 30 days on the US Play Store?"*
- Ranking history chart: *"Can you show me a chart of how com.duolingo's ranking for the keyword 'language learning' has changed over the last 30 days on the US Play Store?"*
- Multi-keyword ranking history chart: *"Can you chart Clash of Clans' ranking for 'game', 'strategy', 'clan', and 'war' over the last 30 days on Google Play?"*
- Keyword metadata: *"What's the search volume and popularity of the keyword 'meditation' on the US Play Store?"*
- Competitor/app lookup: *"Which apps rank for the keyword 'meditation' on the US Play Store?"*
- Organic keywords (costs 50 credits, test carefully): *"Show me the keywords com.duolingo organically ranks for on the US Play Store, for the date 2026-07-01."*
- Organic impression share: *"What's the organic impression share for 'meditation' split across competing apps on the US Play Store?"*
- Share of category: *"What app categories does the keyword 'meditation' fall into on the US Play Store?"*

**Cross-store comparison** ([`tools/compare/example_prompts.txt`](src/mcp_task/tools/compare/example_prompts.txt))

- Keyword metadata: *"Is 'meditation' searched more on the App Store or Google Play?"*
- Keyword ranking: *"Compare Clash of Clans' ranking for 'clan' and 'war' between the App Store and Google Play (App Store id 529479190, Play Store id com.supercell.clashofclans)."*
- Ranking history: *"How has Clash of Clans' ranking for 'strategy game' compared between the App Store and Google Play over the last 15 days?"*
- Top keywords: *"Compare the keywords bringing Clash of Clans the most search volume on the App Store vs Google Play for 2026-07-01."*
- Ranking chart: *"Can you chart Clash of Clans' App Store vs Google Play ranking for 'clan' and 'war'?"*
- Ranking history chart: *"Can you show me a chart comparing Clash of Clans' App Store vs Google Play ranking for 'strategy game' over the last 30 days?"*

## Running the tests

```bash
uv run pytest
```

All tests are network-free (HTTP calls are mocked), so they don't spend API
credits.

## Project layout

```
src/mcp_task/
  errors.py           ToolError, handle_tool_errors, with_credit_usage
  credit_tracking.py  contextvar go-between for with_credit_usage (see Credit awareness)
  clients/     raw HTTP clients (MobileAction, iTunes, unofficial Play scraper)
  services/    validation + fetch logic, reusable across tools
    appstore/    keyword_service.py, app_service.py (iTunes-backed)
    playstore/   keyword_service.py, app_service.py
    cache.py     shared Redis-caching helper (both stores' MobileAction fetches)
  validation/  input validation, split the same way as services/
    common.py    shared validators (country_code, text, date, date_range, positive_int, keyword_list)
    appstore.py  App Store-only (numeric track_id, device, track_id_list)
    playstore.py Play Store-only (package_name, package_name_list)
  charting/    HTML/Chart.js dashboard rendering — generic, reused by any store's chart tools
  tools/       the @mcp.tool definitions themselves
    appstore/    keyword_services.py, app_lookup.py, charts.py, example_prompts.txt
    playstore/   keyword_services.py, app_lookup.py, charts.py, example_prompts.txt
    compare/     keyword_services.py, charts.py — needs BOTH stores, so it's
                 neither appstore/ nor playstore/; see below
    account.py   (not store-specific, stays top-level)
```

Each store is its own subpackage rather than one growing module or a pile of
prefixed files — `services/appstore/` and `services/playstore/` mirror each
other module-for-module, same for `tools/` and `validation/`. Both stores now
have a `charts.py`, sharing the same `charting/` rendering package via
`render_dashboard_html`'s `platform` argument (`charting.dashboard.APP_STORE`
vs `PLAY_STORE` — a `StorePlatform` bundling the device axis to split by and
the display label, since Play Store history entries have no device field at
all and get a single merged view with the toggle hidden instead of a real
iPhone/iPad split). `services/compare/` and `tools/compare/` are a third
category alongside `appstore/`/`playstore/`, for tools that need data from
*both* stores at once (e.g. `compare_stores_keyword_ranking`) — they import
from both stores' service modules directly rather than duplicating fetch
logic, and their charts reuse the same `render_dashboard_html`/`StorePlatform`
mechanism via a third platform, `COMPARE` (a single merged axis labeling each
series by store instead of by device). New tool files (or a whole new store
or compare subpackage) are picked up automatically: `mcp_instance.py`
recursively walks `tools/` at startup (`pkgutil.walk_packages`, not the
non-recursive `iter_modules` — subpackages need the recursive version)
instead of hand-listing imports, so nothing needs to be wired in by hand.

Redis cache keys follow the same split: App Store keys are
`mcp:appstore:<thing>:...`, Play Store keys are `mcp:playstore:<thing>:...` —
always prefix a new cache key with its store name so keys stay
distinguishable at a glance (e.g. in `redis-cli KEYS 'mcp:*'`).

## Adding a new tool

Follow the same three-layer path every existing tool takes:

1. **Client** (`clients/`) — only if you need a new external API. If it's
   another MobileAction endpoint, reuse `clients/mobileaction.py`'s `get()`
   rather than writing a new HTTP call.
2. **Service** (`services/<store>/`) — validate inputs (reuse a validator
   from `validation/common.py` or `validation/<store>.py`, or add a new one
   there if the input shape is new) and call the client function. Wrap the
   call in `services/cache.py`'s `cached()` if the response is safe to cache
   — i.e. the inputs pin down a concrete/historical result, not "whatever is
   most recent right now."
3. **Tool** (`tools/<store>/`) — a thin function stacking three decorators:
   `@mcp.tool` outermost, then `@with_credit_usage`, then `@handle_tool_errors`
   innermost. The body just calls the service and shapes its return value
   into the tool's response dict — no try/except needed; `handle_tool_errors`
   catches `ToolError` (via `to_error_response`) *and* anything unexpected (a
   malformed API response, a third-party library edge case) so a bug never
   leaks a raw Python exception to the model, and `with_credit_usage` attaches
   the credits spent during the call to whatever dict comes out (see
   [Credit awareness](#credit-awareness)). Nothing else to wire up —
   `mcp_instance.py` finds the tool automatically at startup.

Then mirror the same `<store>/` path under `tests/` for each layer you
touched, and add a row to the relevant credits table + an entry in
`tools/<store>/example_prompts.txt` in this README.

Needs data from both stores at once (a comparison)? It goes under
`services/compare/` / `tools/compare/` instead of either store's own
subpackage — see `services/compare/keyword_service.py` for the pattern
(import both stores' service modules, call each with its own id, combine
under `{"app_store": ..., "play_store": ...}`). **Check for a tool-name
collision before naming it** — tool names are global across the whole MCP
server, not namespaced by Python module, and nothing catches a
same-named `@mcp.tool` in a different file at import time (the second
one silently replaces the first in FastMCP's registry, with only a
runtime warning easy to miss). This bit us once already: an App Store tool
comparing multiple apps (now named `compare_appstore_keyword_ranking_history`,
but at the time just `compare_keyword_ranking_history`) already existed
before a cross-store tool was almost given the exact same name (comparing
stores) — hence the `compare_stores_*` prefix for anything that compares
two stores rather than two apps on the same store.
`tests/test_tool_registration.py` now catches this statically (a
duplicate `@mcp.tool` function name anywhere under `tools/` fails the
test suite instead of silently overwriting the registry entry at
runtime) — same file also fails the suite if a new tool forgets
`@handle_tool_errors` outside a `charts.py` file, or forgets
`@with_credit_usage` (no exemption for that one — every tool, chart or not,
must have it).

### Error handling

Every tool that fails returns `{"error": str, "status_code": int | None, "error_type": str}`
instead of raising — `status_code` alone can't tell "bad input" apart from
"not found" apart from "network hiccup" (all three leave it `None`), so
`error_type` is the explicit, machine-readable category (`errors.py`'s
`ToolError` docstring has the full list: `validation`, `not_found`,
`upstream_api`, `network`, `internal`). Each `ToolError` subclass
(`InputValidationError`, `MobileActionAPIError`, `AppLookupError`,
`PlayStoreSearchError`) sets a sensible default and overrides it per raise
site when one subclass covers more than one situation — e.g.
`MobileActionAPIError` derives it from `status_code` automatically (`None` →
`network`, `404` → `not_found`, anything else → `upstream_api`).

Not store-specific (like `tools/account.py` or `services/cache.py`)? Put it
at the top level of `services/`/`tools/` instead of under a store folder.

### Credit awareness

Every tool's response — success or error — carries the credits that the call
actually spent: `credit_cost` (an `int`, summed across every MobileAction API
request the tool made) and `credit_remaining` (the account's balance after
the last of those requests). A tool that fetches one thing (e.g.
`get_appstore_keyword_ranking`) shows the cost of that one call; a tool that fans out
to several apps/stores (e.g. `compare_appstore_keyword_ranking_history` across 5 apps)
shows the *sum* of all of them, not just the last one — the field genuinely
means "what this call cost you," not "what the last request cost." Neither
field appears at all if the response was served from Redis cache (see
[Setup](#setup)) — a cache hit spends zero credits, so there's nothing to
report.

This is implemented with minimal coupling between unrelated modules:
`clients/mobileaction.py` (the producer, reading `X-Credit-Cost`/
`X-Credit-Remaining` off the response) and `errors.py`'s `with_credit_usage`
decorator (the consumer, merging it into the tool's response dict) don't
import each other — both depend on a small, dependency-free go-between,
`credit_tracking.py`, which just holds a `contextvars.ContextVar` (safe
under FastMCP's concurrent tool calls, unlike a plain module global) with
`reset()`/`record()`/`pop()`. `with_credit_usage` is a separate decorator
from `handle_tool_errors` (see step 3 above) rather than folded into it, so
it applies uniformly to every tool — including chart tools, which skip
`handle_tool_errors` entirely.
