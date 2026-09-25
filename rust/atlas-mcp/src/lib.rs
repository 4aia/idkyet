//! Atlas MCP server on Cloudflare Workers: a thin, read-only wrapper around
//! the internal Atlas REST API, exposed to AI agents over MCP. Replaces the
//! (retired) Python and Go implementations of the same server.
//!
//! Transport: Streamable HTTP in plain-JSON-response mode (single
//! `application/json` body per POST to `/mcp`, no SSE/session bookkeeping —
//! this server never pushes a message outside of replying to a request, so
//! the simpler mode is spec-legal and fits Workers' request/response model
//! far better than a long-lived SSE stream would).

mod atlas_api;
mod catalog;
mod mcp;
mod prompts;
mod ratelimit;
mod tools;

use serde_json::{json, Value};
use worker::{event, Context, Env, Headers, Request, Response, ResponseBody, Result};

use atlas_api::Client;
use mcp::AppContext;

#[event(fetch)]
async fn main(req: Request, env: Env, _ctx: Context) -> Result<Response> {
    let path = req.path();

    if path == "/llms.txt" {
        return text_response(LLMS_TXT, 200);
    }

    if path != "/mcp" {
        return text_response("Not Found", 404);
    }

    if req.method() == worker::Method::Options {
        return cors_preflight();
    }

    if req.method() != worker::Method::Post {
        return text_response(BROWSER_INFO, 200);
    }

    let client_ip = ratelimit::client_ip(&req);
    if let Some(ip) = client_ip.as_deref()
        && !ratelimit::allow(&env, ip).await {
            return json_response(
                &json!({
                    "error": "rate_limited",
                    "message": "MCP rate limit exceeded.",
                }),
                429,
            );
        }

    let mut req = req;
    let body: Value = match req.json().await {
        Ok(v) => v,
        Err(_) => {
            return json_response(
                &json!({ "jsonrpc": "2.0", "id": null, "error": { "code": -32700, "message": "parse error" } }),
                400,
            )
        }
    };

    let client = Client::new(&env)?;
    let ctx = AppContext { client, client_ip };

    match mcp::handle(body, &ctx).await {
        Some(response) => json_response(&response, 200),
        // A notification (e.g. notifications/initialized) gets no body.
        None => Response::empty().map(|r| r.with_status(202)).map(with_cors),
    }
}

const BROWSER_INFO: &str = "Atlas MCP server. Connect with an MCP client (streamable HTTP) at \
    /mcp, e.g.: claude mcp add --transport http atlas https://<this-worker>/mcp";

const LLMS_TXT: &str = "# Atlas MCP Server\n\n\
    > Remote MCP server (streamable HTTP) for German open data: live and archived data for the \
    largest German cities, from licensed official sources with per-record attribution. Keyless \
    and read-only.\n\n\
    Endpoint: /mcp\n";

fn json_response(value: &Value, status: u16) -> Result<Response> {
    let headers = Headers::new();
    headers.set("Content-Type", "application/json")?;
    let body = value.to_string().into_bytes();
    Response::from_body(ResponseBody::Body(body))
        .map(|r| r.with_headers(headers))
        .map(|r| r.with_status(status))
        .map(with_cors)
}

fn text_response(text: &str, status: u16) -> Result<Response> {
    Response::ok(text)
        .map(|r| r.with_status(status))
        .map(with_cors)
}

fn cors_preflight() -> Result<Response> {
    Response::empty().map(|r| r.with_status(204)).map(with_cors)
}

fn with_cors(resp: Response) -> Response {
    let headers = resp.headers().clone();
    let _ = headers.set("Access-Control-Allow-Origin", "*");
    let _ = headers.set("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
    let _ = headers.set("Access-Control-Allow-Headers", "Content-Type, Accept, Mcp-Session-Id");
    resp.with_headers(headers)
}
