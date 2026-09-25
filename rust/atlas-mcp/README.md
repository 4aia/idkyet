# Atlas MCP server (Rust, Cloudflare Workers)

Replaces the retired Python (`src/infranode/mcp/`) and Go (`go/`, since
removed) implementations. Same behavior, same tool surface, same security
gates (slug/EVA/resource-allowlist validation) — just deployed as a
Cloudflare Worker instead of a self-hosted process. It's a thin, read-only
HTTP client wrapper around the internal Atlas REST API: no mapping or
licensing logic lives here.

## Why Rust + Workers

Everything on Cloudflare's free tier, no Docker/VPS to run or pay for:
Workers (100k requests/day free), the native Rate Limiting binding, and (for
the REST API, separately, not yet started) KV/D1. Rust is one of the two
languages with first-class, non-experimental support on Workers (the other
being JS/TS); Python-on-Workers exists but its compatibility with this
codebase's dependencies (httpx, a TCP-based Redis client) is unverified and
was deliberately not gambled on for a 45k-line rewrite.

## Layout

- `src/atlas_api.rs` — the loopback HTTP client: resource/collection/
  live-resource/station-board allowlists, slug/EVA validation, graceful
  5xx-to-envelope handling. Pure logic is unit-tested with plain `cargo test`
  (no wasm/Workers runtime needed for that part).
- `src/mcp.rs` — hand-rolled MCP JSON-RPC dispatch (no Rust MCP SDK crate was
  verified to work in the Workers/wasm32 runtime, which has no Tokio; the
  protocol surface needed here — initialize/tools/resources/prompts — is
  small enough to implement directly).
- `src/tools.rs` — the 12 tool schemas + handlers.
- `src/catalog.rs` — the 3 resources (`atlas://cities`, `atlas://sources`,
  `atlas://catalog`).
- `src/prompts.rs` — the 4 ready-made prompts.
- `src/ratelimit.rs` — client-IP extraction (`CF-Connecting-IP`) and the
  Workers-native Rate Limiting binding wrapper.

## Transport

Streamable HTTP in plain-JSON-response mode: one `application/json` body per
POST to `/mcp`, no SSE stream and no `Mcp-Session-Id` bookkeeping. This
server never needs to push a message outside of replying to a request, so
the simpler mode (explicitly legal per the MCP spec) fits Workers'
request/response model far better than a long-lived SSE connection would.

## Develop

```bash
cargo test                                    # pure-logic unit tests, native target
cargo build --target wasm32-unknown-unknown   # confirms it compiles for the real target
npx wrangler dev                              # local dev server (builds via worker-build)
```

Set `ATLAS_API_BASE` in `wrangler.toml` (or `wrangler dev --var ATLAS_API_BASE:...`)
to point at a running Atlas REST API instance.

## Deploy

```bash
npx wrangler deploy
```

Requires a (free) Cloudflare account and `wrangler login`. The Rate Limiting
binding (`[[unsafe.bindings]]` in `wrangler.toml`) is provisioned
automatically on first deploy.

## Known gaps

- **The REST API hasn't moved to Cloudflare yet.** This Worker calls
  `ATLAS_API_BASE` over plain HTTP; wherever that API actually runs still
  needs to be reachable from Cloudflare's network. Porting the REST API
  itself (adapters, normalizers, KV-backed caching, D1-backed stores) is a
  separate, much larger effort not started here.
- **CORS is wide open** (`Access-Control-Allow-Origin: *`), matching the
  REST API's own keyless/public posture. Tighten if that ever changes.
- Rate limiting uses Cloudflare's native per-request binding (simple,
  fixed-window-ish, "intentionally not built for precise accounting" per
  Cloudflare's own docs) rather than a hand-rolled moving window. Good enough
  for abuse protection; not a precision quota system.
