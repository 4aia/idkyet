//! Real client-IP extraction and the per-IP rate-limit check for the public
//! endpoint. Uses Cloudflare's native Workers Rate Limiting binding (a
//! purpose-built primitive for exactly this) rather than hand-rolling a
//! counter in KV, which would be both slower (an extra read+write per
//! request) and no more accurate (KV is eventually consistent too).

use worker::Env;

/// `CF-Connecting-IP` is set verbindlich by Cloudflare on every request that
/// reaches a Worker, so no X-Forwarded-For fallback is needed the way a
/// self-hosted origin behind Cloudflare would need one.
pub fn client_ip(req: &worker::Request) -> Option<String> {
    req.headers().get("CF-Connecting-IP").ok().flatten()
}

/// Binding name configured in wrangler.toml under `[[unsafe.bindings]]`.
const BINDING: &str = "MCP_RATE_LIMITER";

/// Returns `true` if the request is within budget (or the binding isn't
/// configured, e.g. in local `wrangler dev` without `--experimental-*`
/// flags — fail open locally, fail closed only matters in production where
/// the binding is always present).
pub async fn allow(env: &Env, key: &str) -> bool {
    match env.rate_limiter(BINDING) {
        Ok(limiter) => limiter
            .limit(key.to_string())
            .await
            .map(|o| o.success)
            .unwrap_or(true),
        Err(_) => true,
    }
}
