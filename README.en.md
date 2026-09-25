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

84 cities, around 82 data types:

- **Weather & environment** — weather, weather warnings, air quality,
  pollen/UV, water levels, flooding, wildfire risk
- **Mobility** — real-time transit departures, station boards, traffic,
  parking, charging infrastructure, sharing, fuel prices
- **City & people** — demographics, health, education, events, council
  records, points of interest
- **Economy** — land values, business tax rates, public procurement
- **Energy & vehicles** — electricity prices, solar, district heating,
  vehicle registrations

Sources include: German Weather Service (DWD), Federal Environment Agency
(UBA), Deutsche Bahn, VBB, SMARD, BORIS, Bundesnetzagentur, KBA,
OpenStreetMap, GovData.

## Running it locally

```bash
cp .env.example .env
docker compose -f deploy/docker-compose.yml up
curl http://localhost/api/v1/health
```

Run the MCP server against the local API:

```bash
uv sync --group mcp
INFRANODE_MCP_API_BASE=http://localhost/api/v1 uv run python -m infranode.mcp.server
```

All settings use the `INFRANODE_` env prefix (see `.env.example`). Real
secrets never go in the repo; only `.env.example` is committed.

## Status

The MCP server is currently being migrated from Python to Go; the REST API
stays Python for now. Both run side by side until cutover, with no change
to the public MCP interface.

## License

Closed source, all rights reserved (see [LICENSE](./LICENSE)). The data
passed through keeps the license of its upstream source (e.g. ODbL for
OpenStreetMap, attribution required for DWD) — every response carries its
own `attribution`.
