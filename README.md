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

**Account**
| Tool | Description |
|---|---|
| `get_remaining_api_credits` | Check the MobileAction API key's credit balance. |

**Keyword Services** (MobileAction `/appstore-keyword-ranking/*`)
| Tool | Description |
|---|---|
| `get_keyword_ranking` | Current rank for one or more keywords, one day. |
| `get_top_keywords` | Keywords bringing an app the most search volume. |
| `get_keyword_ranking_history` | Rank history for one keyword over a date range. |
| `get_keyword_metadata` | Search volume/popularity for a keyword, independent of any app. |
| `get_apps_for_keyword` | Which apps rank for a given keyword (competitor discovery). |
| `get_organic_keywords` | Full list of keywords an app organically ranks for. **Costs 50 credits per call.** |

**App lookup** (helper — calls Apple's free iTunes API, not MobileAction, since
MobileAction's endpoints need a numeric `trackId` rather than an app name)
| Tool | Description |
|---|---|
| `get_app_store_id` | Resolve an app name to its numeric App Store id. |
| `get_app_name` | Resolve a numeric App Store id back to its name. |

**Interactive charts** (bonus — render the keyword data above as a
self-contained HTML page with a live Chart.js chart, instead of raw JSON)
| Tool | Description |
|---|---|
| `plot_keyword_ranking` | Bar chart of one app's rank across several keywords. |
| `plot_keyword_ranking_history` | Line chart of one app's rank over time. |
| `compare_keyword_ranking_history` | Line chart comparing 2–5 apps' rank over time. |

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
uv run mcp-task
```

This prints the registered tools and starts listening on stdio. Press
`Ctrl+C` to stop — this mode is just to confirm the server boots and your API
key is picked up; a real client (below) is how you actually use it.

## Connecting with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run mcp-task
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
      "args": ["--directory", "/absolute/path/to/mcp-task", "run", "mcp-task"]
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
