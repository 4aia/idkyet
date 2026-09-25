# Atlas MCP server (Go)

Replaces `src/infranode/mcp/` (Python/FastMCP). Same behavior, same tool
surface, same security gates (SSRF host allowlist, resource/collection
allowlists, slug/EVA validation) — just a different language. It is a thin,
read-only HTTP client wrapper around the internal Atlas REST API: no mapping
or licensing logic lives here, that stays entirely in the (still Python)
REST API.

## Layout

- `cmd/atlas-mcp` — entrypoint; picks stdio vs. streamable-http via
  `INFRANODE_MCP_TRANSPORT`.
- `internal/atlasapi` — the loopback HTTP client (mirrors `mcp/client.py`):
  base-URL host allowlist, resource/collection/live-resource allowlists,
  slug/EVA validation, graceful 5xx-to-envelope handling.
- `internal/atlasmcp` — builds the `*mcp.Server`: 12 tools, 3 resources
  (`atlas://cities`, `atlas://sources`, `atlas://catalog`), 4 prompts.
- `internal/httpmw` — per-IP rate limiting, a concurrency cap, and real
  client-IP propagation for the remote (streamable-http) endpoint (mirrors
  `mcp/ratelimit.py` + `mcp/clientip.py`).

## Run

```bash
go run ./cmd/atlas-mcp                                   # stdio, against localhost:8000
INFRANODE_MCP_API_BASE=http://localhost:8000/api/v1 \
  go run ./cmd/atlas-mcp                                  # explicit API base

INFRANODE_MCP_TRANSPORT=streamable-http \
INFRANODE_MCP_PORT=8081 \
  go run ./cmd/atlas-mcp                                  # remote endpoint on :8081
```

## Test

```bash
go test ./...
```

`internal/atlasmcp` has an end-to-end test using the SDK's in-memory
transport against a mocked REST API (`httptest`), so tool schemas, the
generic `get_city_resource` enum, and error handling are exercised without a
running Python API.

## Known gaps vs. the Python implementation

- **Rate limiting is process-local.** The Python server shares its
  moving-window budget across replicas via Redis
  (`INFRANODE_REDIS_URL`); this one doesn't yet. Fine for a single instance,
  revisit before scaling horizontally.
- **`INFRANODE_MCP_BACKLOG`/keep-alive tuning** from the Python side's
  uvicorn config isn't ported; Go's `net/http` defaults are used instead.
- The `Dockerfile` here hasn't been build-verified in this environment (no
  Docker daemon available) — check it builds before relying on it in
  `deploy/`.

## Status

This is a fresh implementation, not yet wired into `deploy/`. The Python MCP
server (`deploy/Dockerfile.mcp`) stays the one actually deployed at
`mcp.woof.systems` until this has been run against the real REST API and
verified end-to-end.
