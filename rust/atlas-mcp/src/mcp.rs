//! Minimal MCP (Model Context Protocol) JSON-RPC layer: just enough of the
//! spec for this server's needs (initialize, tools, resources, prompts),
//! hand-rolled instead of pulling in a Rust MCP SDK crate, since none of the
//! ones available were verified to work in the Workers/wasm32 runtime (no
//! Tokio here). The wire format matches the spec's Streamable HTTP transport
//! in its plain-JSON-response mode (a single `application/json` body per
//! POST, no SSE/session-id bookkeeping) — valid per spec for servers that
//! never need to push a message outside of replying to a request, which is
//! all this server ever does.

use serde_json::{json, Value};

use crate::atlas_api::Client;

pub const PROTOCOL_VERSION: &str = "2025-06-18";

pub struct AppContext {
    pub client: Client,
    pub client_ip: Option<String>,
}

/// Handles one JSON-RPC request/notification. Returns `None` for
/// notifications (no `id`), which get no response body at all.
pub async fn handle(body: Value, ctx: &AppContext) -> Option<Value> {
    let id = body.get("id").cloned();
    let method = body.get("method").and_then(Value::as_str).unwrap_or("");
    let params = body.get("params").cloned().unwrap_or(Value::Null);

    // A notification (no id) never gets a reply, per JSON-RPC 2.0.
    let id = id?;

    let result = match method {
        "initialize" => Ok(initialize_result()),
        "notifications/initialized" => Ok(Value::Null), // shouldn't normally have an id, handled defensively
        "ping" => Ok(json!({})),
        "tools/list" => Ok(crate::tools::list_tools()),
        "tools/call" => crate::tools::call(&params, ctx).await,
        "resources/list" => Ok(crate::catalog::list_resources()),
        "resources/read" => crate::catalog::read_resource(&params, ctx).await,
        "prompts/list" => Ok(crate::prompts::list_prompts()),
        "prompts/get" => crate::prompts::get_prompt(&params),
        other => Err(RpcError {
            code: -32601,
            message: format!("method not found: {other}"),
        }),
    };

    Some(match result {
        Ok(value) => json!({ "jsonrpc": "2.0", "id": id, "result": value }),
        Err(e) => json!({
            "jsonrpc": "2.0",
            "id": id,
            "error": { "code": e.code, "message": e.message },
        }),
    })
}

#[derive(Debug)]
pub struct RpcError {
    pub code: i64,
    pub message: String,
}

impl RpcError {
    pub fn invalid_params(message: impl Into<String>) -> Self {
        Self {
            code: -32602,
            message: message.into(),
        }
    }
}

fn initialize_result() -> Value {
    let data_type_count = crate::atlas_api::ALLOWED_RESOURCES.len() - 1; // "overview" is the meta resource itself
    let tool_count = crate::tools::TOOL_COUNT;
    json!({
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {
            "tools": { "listChanged": false },
            "resources": { "listChanged": false },
            "prompts": { "listChanged": false },
        },
        "serverInfo": { "name": "atlas", "title": "Atlas", "version": "1.0.0" },
        "instructions": instructions(data_type_count, tool_count),
    })
}

fn instructions(data_type_count: usize, tool_count: usize) -> String {
    format!(
        "Atlas is a keyless, read-only open-data API for 84 German cities with \
        ~{data_type_count} data types, exposed as {tool_count} MCP tools. To answer ANY city \
        question, START with get_city_overview(slug): it returns the city's base data, a \
        catalog of ALL available data types (each with its coverage status and the exact tool \
        to call next) and a small live snapshot (weather, air, train departures). Most data \
        types are fetched with ONE generic tool: get_city_resource(slug, resource=<type>), \
        where <type> is the catalog key (e.g. 'parking', 'charging', 'demographics', 'solar'); \
        its resource enum lists every valid key. City slugs are resolved leniently: you may \
        pass the German name with or without umlauts, any casing, a common English exonym or a \
        short form (e.g. 'muenchen', 'München', 'munich', 'munchen', 'cologne', 'frankfurt' all \
        resolve to the canonical slug), so you rarely need the exact ASCII slug; an unrecognized \
        name returns a 404 whose hint names the closest match ('Meintest du ...?'). Discover the \
        canonical slugs with list_cities (or the atlas://cities resource); browse every data \
        type with the atlas://catalog resource; see sources and licenses with sources. Compare \
        one metric across many cities in one call with compare. Every tool returns a canonical \
        {{data, meta}} envelope; meta.source_status tells you whether a source delivered data \
        (ok / no_data / not_covered / disabled / error), so a missing source degrades gracefully \
        instead of failing. Field names are snake_case and English across all data types \
        (post_code, street, house_number, place, name, start, end, distance_km, power_kw, lat, \
        lon); timestamps carry a time zone and a missing value is null, never an empty string. \
        The atlas://catalog resource spells the conventions out. Coverage keeps growing: more \
        data types and cities are added regularly."
    )
}
