[Deutsch](./README.md) | English

# Atlas

An MCP server for open data about German cities — weather, air quality,
public transit, traffic, energy, demographics and more, behind a handful of
tools instead of 25 different government APIs with their own formats.

## Why

German cities and public agencies publish a lot of open data, but every
source has its own format, field names and quirks. Atlas normalizes about
25 upstream sources (DWD, UBA, Deutsche Bahn, SMARD, BORIS,
Bundesnetzagentur, OpenStreetMap, GovData, ...) into one shared schema and
exposes them to AI agents over MCP. No API key, no account, no 25 APIs to
learn.

## Getting started

One call is enough: `get_city_overview(slug)` returns a city's base data,
a catalog of every available data type (with coverage status and the
matching tool) and a small live snapshot (weather, air, train departures).
From there, either use a few named tools (`weather`, `air_quality`, `pois`,
`compare`, the station boards) or the generic
`get_city_resource(slug, resource=<key>)` for everything else.

City names resolve leniently: with or without umlauts, any casing, common
English exonyms (`munich`, `cologne`, ...). An unrecognized name returns a
suggestion instead of a bare error.

## Connect

```bash
claude mcp add --transport http atlas https://mcp.woof.systems/mcp
```

Any other MCP client (Cursor, Windsurf, Claude Desktop, a ChatGPT connector)
against the same remote endpoint:

```jsonc
{
  "mcpServers": {
    "atlas": { "url": "https://mcp.woof.systems/mcp" }
  }
}
```

Every tool is read-only (`readOnlyHint`, `idempotentHint`), so MCP clients
can approve them without asking. Details, the full tool manifest with
example output, and the permission model live in
[docs/mcp-install.md](./docs/mcp-install.md). The registry manifest is
[server.json](./server.json).

## How it works

A shared HTTP client queries the upstream sources, each response is mapped
onto a canonical `{ data, meta }` schema, run through the license gate
(per-record attribution) and cached in Redis (with stale-on-error
fallback). If a source is down, that shows up in `meta.source_status` — the
call itself doesn't fail because of it.

The REST API behind it is an internal implementation detail; the MCP
server is the only public interface.

Field names are snake_case and English across every data type, and the
same concept always uses the same name (`post_code`, `street`, `lat`,
`lon`, `start`, `end`, ...). A value the source doesn't provide is `null`,
never an empty string.

## Data

84 cities, 44 data types — every single one a real live request per call, no
offline/batch data:

- **Weather & environment** — weather, weather warnings, air quality,
  pollen/UV, water levels, flooding, wildfire risk, bathing water quality
- **Mobility** — real-time transit departures, station boards, traffic,
  parking, charging infrastructure (live status), sharing, fuel prices
- **City & people** — demographics, health, events, council records (live
  OParl per city), heritage sites, tree cadastre
- **Economy** — land values, public procurement
- **Energy** — electricity prices, solar irradiance

Sources include: German Weather Service (DWD), Federal Environment Agency
(UBA), Deutsche Bahn, VBB, SMARD, BORIS (per federal state), nextbike/GBFS,
Wikidata, and individual cities' own OParl systems.

## Running it locally

REST API directly (no Docker needed):

```bash
cp .env.example .env
uv sync
uv run uvicorn infranode.main:app --reload
curl http://localhost:8000/api/v1/health
```

MCP server (Rust, [rust/atlas-mcp](./rust/atlas-mcp)) against the local API:

```bash
cd rust/atlas-mcp
npx wrangler dev   # set ATLAS_API_BASE in wrangler.toml to http://localhost:8000/api/v1
```

All REST API settings are plain camelCase variables with no prefix (see
`.env.example`). Real secrets never go in the repo; only `.env.example` is
committed.

## Status

The MCP server has been fully moved to **Rust on Cloudflare Workers**
([rust/atlas-mcp](./rust/atlas-mcp)) — free tier, no Docker/VPS. The REST API
still runs as a Python process for now; moving it to Cloudflare too (KV
instead of Redis, D1 instead of the local stores) is planned but not started.

## License

Closed source, all rights reserved (see [LICENSE](./LICENSE)). The data
passed through keeps the license of its upstream source (e.g. ODbL for
OpenStreetMap, attribution required for DWD) — every response carries its
own `attribution`.
