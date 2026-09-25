//! MCP resources: `atlas://cities`, `atlas://sources` (both live API calls,
//! passed through unchanged) and `atlas://catalog` (a static, computed list
//! of every per-city data type and the tool that fetches it).

use serde_json::{json, Value};

use crate::atlas_api::generic_resources;
use crate::mcp::{AppContext, RpcError};

pub fn list_resources() -> Value {
    json!({
        "resources": [
            {
                "uri": "atlas://cities",
                "name": "cities",
                "description": "All covered German cities with slug, federal state, population \
                    and coverage.",
                "mimeType": "application/json",
            },
            {
                "uri": "atlas://sources",
                "name": "sources",
                "description": "All Atlas data sources with license, attribution and \
                    availability.",
                "mimeType": "application/json",
            },
            {
                "uri": "atlas://catalog",
                "name": "catalog",
                "description": "The catalog of all per-city data types: label, matching tool \
                    and REST path. Lets an agent browse the full breadth of Atlas without a \
                    tool call.",
                "mimeType": "application/json",
            },
        ]
    })
}

pub async fn read_resource(params: &Value, ctx: &AppContext) -> Result<Value, RpcError> {
    let uri = params
        .get("uri")
        .and_then(Value::as_str)
        .ok_or_else(|| RpcError::invalid_params("missing resource uri"))?;

    let body = match uri {
        "atlas://cities" => ctx
            .client
            .get_collection("cities", &[("limit", "200")], ctx.client_ip.as_deref())
            .await
            .map_err(|e| RpcError {
                code: -32603,
                message: e.message,
            })?,
        "atlas://sources" => ctx
            .client
            .get_collection("sources", &[("limit", "200")], ctx.client_ip.as_deref())
            .await
            .map_err(|e| RpcError {
                code: -32603,
                message: e.message,
            })?,
        "atlas://catalog" => build_catalog(),
        other => {
            return Err(RpcError {
                code: -32002,
                message: format!("resource not found: {other}"),
            })
        }
    };

    Ok(json!({
        "contents": [{
            "uri": uri,
            "mimeType": "application/json",
            "text": body.to_string(),
        }]
    }))
}

fn build_catalog() -> Value {
    let mut data_types: Vec<Value> = vec![
        json!({ "type": "base", "tool": "get_city", "path": "/api/v1/cities/{slug}/base" }),
        json!({
            "type": "overview",
            "tool": "get_city_overview",
            "path": "/api/v1/cities/{slug}/overview",
        }),
    ];
    let mut resources = generic_resources();
    resources.retain(|r| *r != "base" && *r != "overview");
    for r in resources {
        data_types.push(json!({
            "type": r,
            "tool": "get_city_resource",
            "path": format!("/api/v1/cities/{{slug}}/{r}"),
        }));
    }
    data_types.sort_by(|a, b| a["type"].as_str().cmp(&b["type"].as_str()));

    json!({
        "data_types": data_types,
        "note": "Atlas keeps adding more data types and cities. Start with \
            get_city_overview(slug) for a live, per-city view. Where 'tool' is \
            get_city_resource, pass the 'type' value as its resource argument.",
        "field_conventions": {
            "naming": "Fields are snake_case and English across all data types. The same \
                concept always uses the same name: post_code, street, house_number, place, \
                name, start, end, distance_km, power_kw, lat, lon.",
            "types": "post_code is always a five-character string, so leading zeros survive \
                (01067). Coordinates are numbers (lat/lon, WGS84). Timestamps are ISO 8601 and \
                always carry a time zone. A value the source does not provide is null, never an \
                empty string.",
        },
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catalog_covers_every_generic_resource_including_base_and_overview() {
        // base/overview are part of generic_resources() too (only "pois" is
        // excluded); build_catalog() just lists them first, not twice.
        let catalog = build_catalog();
        let data_types = catalog["data_types"].as_array().unwrap();
        assert_eq!(data_types.len(), generic_resources().len());
    }
}
