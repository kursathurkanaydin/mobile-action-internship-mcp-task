# MobileAction MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes MobileAction's
**App Store Keyword Services** API as tools an LLM (Claude Desktop, Cursor,
MCP Inspector, etc.) can call directly. Ask something like *"What keywords
does Duolingo rank best for on the US App Store?"* and the model resolves the
app, calls the right tool, and answers from real MobileAction data.

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
per call, not per keyword (e.g. `get_keyword_ranking` costs 3 credits whether
you pass one keyword or four).

**Account**
| Tool | Description | Credits/call |
|---|---|---|
| `get_remaining_api_credits` | Check the MobileAction API key's credit balance. | Free |

**Keyword Services** (MobileAction `/appstore-keyword-ranking/*`)
| Tool | Description | Credits/call |
|---|---|---|
| `get_keyword_ranking` | Current rank for one or more keywords, one day. | 3 |
| `get_apps_for_keyword` | Which apps rank for a given keyword (competitor discovery). | 5 |
| `get_keyword_metadata` | Search volume/popularity for a keyword, independent of any app. | 5 |
| `get_keyword_ranking_history` | Rank history for one keyword for an app over a date range. | 10 |
| `get_top_keywords` | Keywords bringing an app the most search volume. | 20 |
| `get_organic_keywords` | Full list of keywords an app organically ranks for. | **50** |

**App lookup** (helper — calls Apple's free iTunes API, not MobileAction, since
MobileAction's endpoints need a numeric `trackId` rather than an app name)
| Tool | Description | Credits/call |
|---|---|---|
| `get_app_store_id` | Resolve an app name to its numeric App Store id. | Free (external API) |
| `get_app_name` | Resolve a numeric App Store id back to its name. | Free (external API) |

**Interactive charts** (bonus — render the keyword data above as a
self-contained HTML page with a live Chart.js chart, instead of raw JSON).
Cost is just the underlying MobileAction call(s) they wrap — no extra charge
for rendering.
| Tool | Description | Credits/call |
|---|---|---|
| `plot_keyword_ranking` | Bar chart of one app's rank across several keywords. | 3 (same as `get_keyword_ranking`) |
| `plot_keyword_ranking_history` | Line chart of one app's rank over time. | 10 (same as `get_keyword_ranking_history`) |
| `compare_keyword_ranking_history` | Line chart comparing 2–5 apps' rank over time. | 10 × number of apps (one history call per app) |

### Example requests

What each tool actually calls under the hood (`529479190` = Clash of Clans'
trackId, `US` storefront, keyword `strategy`). The two chart tools that plot
a single app/keyword (`plot_keyword_ranking`, `plot_keyword_ranking_history`)
hit the exact same endpoints as `get_keyword_ranking` /
`get_keyword_ranking_history` below — they just render the response as a
chart instead of returning it raw; `compare_keyword_ranking_history` calls
the `get_keyword_ranking_history` endpoint once per app being compared.

```
get_remaining_api_credits
  GET https://api.mobileaction.co/api-key?token=YOUR_API_KEY

get_keyword_ranking
  GET https://api.mobileaction.co/appstore-keyword-ranking/529479190/US/keywordrankings
      ?keywords=strategy&token=YOUR_MOBILEACTION_API_KEY

get_top_keywords
  GET https://api.mobileaction.co/appstore-keyword-ranking/529479190/US/top-keywords
      ?date=2026-07-01&token=YOUR_MOBILEACTION_API_KEY

get_keyword_ranking_history
  GET https://api.mobileaction.co/appstore-keyword-ranking/529479190/US/strategy/keywordrankings
      ?startDate=2026-07-01&endDate=2026-07-15&token=YOUR_MOBILEACTION_API_KEY

get_keyword_metadata
  GET https://api.mobileaction.co/appstore-keyword-ranking/US/keyword-metadata
      ?keyword=strategy&token=YOUR_MOBILEACTION_API_KEY

get_apps_for_keyword
  GET https://api.mobileaction.co/appstore-keyword-ranking/US/keyword-apps
      ?keyword=strategy&token=YOUR_MOBILEACTION_API_KEY

get_organic_keywords
  GET https://api.mobileaction.co/appstore-keyword-ranking/529479190/US/IPHONE/organic-keywords
      ?date=2026-07-01&token=YOUR_MOBILEACTION_API_KEY

get_app_store_id                                 (Apple's iTunes API, not MobileAction)
  GET https://itunes.apple.com/search?term=Clash+of+Clans&entity=software&country=us&limit=1

get_app_name                                     (Apple's iTunes API, not MobileAction)
  GET https://itunes.apple.com/lookup?id=529479190&country=us
```

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

## Running it standalone (sanity check)

```bash
uv run src/mcp-task/server.py
```

This starts listening on stdio. Press
`Ctrl+C` to stop — this mode is just to confirm the server boots and your API
key is picked up; a real client (below) is how you actually use it.

## Connecting with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run src/mcp-task/server.py
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
      "args": ["--directory", "/absolute/path/to/mcp-task", "run", "src/mcp-task/server.py"]
    }
  }
}
```

Restart Claude Desktop, then ask it something like *"What's my MobileAction
credit balance?"* or *"Show me the top keywords for Duolingo on the US App
Store for 2026-07-01."*

## Running the tests

```bash
uv run pytest
```

All tests are network-free (HTTP calls are mocked), so they don't spend API
credits.

## Project layout

```
src/mcp_task/
  clients/     raw HTTP clients (MobileAction, iTunes)
  services/    validation + fetch logic, reusable across tools
  charting/    HTML/Chart.js dashboard rendering
  tools/       the @mcp.tool definitions themselves
```
