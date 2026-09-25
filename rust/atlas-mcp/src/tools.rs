//! Tool definitions (schemas for tools/list) and handlers (tools/call).
//! Every handler is a thin wrapper around `atlas_api::Client` — no mapping or
//! licensing logic lives here, mirroring the Python/Go implementations this
//! replaces.

use serde_json::{json, Value};

use crate::atlas_api::{Client, UpstreamError};
use crate::mcp::{AppContext, RpcError};

pub const TOOL_COUNT: usize = 12;

const SLUG_DESCRIPTION: &str = "City identifier, e.g. 'berlin' or 'hamburg'. Resolved leniently: \
    the German name with or without umlauts, any casing, a common English exonym or short form \
    also works (München/munich/munchen -> muenchen, cologne -> koeln, frankfurt -> \
    frankfurt-am-main). An unknown name returns 404 with a 'Meintest du ...?' suggestion. \
    list_cities gives the canonical slugs.";

fn annotations(title: &str, open_world: bool) -> Value {
    json!({
        "title": title,
        "readOnlyHint": true,
        "destructiveHint": false,
        "idempotentHint": true,
        "openWorldHint": open_world,
    })
}

fn slug_schema() -> Value {
    json!({
        "type": "object",
        "properties": { "slug": { "type": "string", "description": SLUG_DESCRIPTION } },
        "required": ["slug"],
    })
}

fn no_args_schema() -> Value {
    json!({ "type": "object", "properties": {} })
}

pub fn list_tools() -> Value {
    let resource_enum: Vec<&str> = crate::atlas_api::generic_resources();

    let tools = vec![
        json!({
            "name": "get_city",
            "title": "City Base Data",
            "description": "Get base data for a German city (population, area, coordinates). \
                Sourced from Wikidata. Read-only. Useful as a first lookup to confirm a city \
                exists and get its core attributes. For a broader question about the city use \
                get_city_overview instead.",
            "inputSchema": slug_schema(),
            "annotations": annotations("City Base Data", true),
        }),
        json!({
            "name": "get_city_overview",
            "title": "City Overview",
            "description": "Get a ONE-CALL overview of everything Atlas knows about a German \
                city. Start here for any city question. Returns: the city's base data, a \
                CATALOG of all available data types with coverage status and the exact tool to \
                call next, plus a small live highlights snapshot (current weather, air quality \
                and train departures). Read-only.",
            "inputSchema": slug_schema(),
            "annotations": annotations("City Overview", true),
        }),
        json!({
            "name": "get_city_resource",
            "title": "City Data by Type",
            "description": "Fetch ANY per-city data type by its key (generic accessor). One \
                tool for the whole breadth of Atlas: live data, statistics, multi-year time \
                series, infrastructure and environment data, and more. Discover the valid keys \
                and per-city coverage with get_city_overview(slug) or the atlas://catalog \
                resource; the resource enum lists every key. Uncovered types return \
                source_status=\"not_covered\" (plus where they ARE available), never an error. \
                Read-only.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "slug": { "type": "string", "description": SLUG_DESCRIPTION },
                    "resource": {
                        "type": "string",
                        "enum": resource_enum,
                        "description": "Data type key to fetch, exactly as listed by \
                            get_city_overview / the atlas://catalog resource (the 'type' \
                            field), e.g. 'charging', 'parking', 'demographics', 'solar', \
                            'district-heating'.",
                    },
                },
                "required": ["slug", "resource"],
            },
            "annotations": annotations("City Data by Type", true),
        }),
        json!({
            "name": "air_quality",
            "title": "Air Quality",
            "description": "Get official air quality for a German city (PM10, NO2 and more). \
                Sourced from the Umweltbundesamt (UBA). Read-only. For live nearest-station \
                hourly readings use get_city_resource(slug, resource='air') instead.",
            "inputSchema": slug_schema(),
            "annotations": annotations("Air Quality", true),
        }),
        json!({
            "name": "weather",
            "title": "Weather",
            "description": "Get current weather observations for a German city. Sourced from \
                the Deutscher Wetterdienst (DWD). Read-only, current conditions only (not a \
                forecast). For warnings use get_city_resource(slug, \
                resource='weather-warnings').",
            "inputSchema": slug_schema(),
            "annotations": annotations("Weather", true),
        }),
        json!({
            "name": "pois",
            "title": "Points of Interest",
            "description": "Get points of interest in a German city, filtered by type. \
                Sourced from OpenStreetMap. Read-only.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "slug": { "type": "string", "description": SLUG_DESCRIPTION },
                    "type": {
                        "type": "string",
                        "description": "POI type from the API allowlist, one of: hospital, \
                            school, pharmacy, restaurant, police, kindergarten.",
                    },
                },
                "required": ["slug", "type"],
            },
            "annotations": annotations("Points of Interest", true),
        }),
        json!({
            "name": "station_board_departures",
            "title": "Station Board: Departures",
            "description": "Get live departures for ANY railway station by its EVA number. \
                Covers all train categories including local/regional (S/RB/RE) and long \
                distance, with real-time delays, cancellations and disruption messages. Get the \
                EVA from get_city_resource(slug, resource='stations'). Read-only.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "eva": {
                        "type": "string",
                        "description": "Station EVA number (digits only) from \
                            get_city_resource(slug, resource='stations'), e.g. '8011160' \
                            (Berlin Hbf).",
                    },
                },
                "required": ["eva"],
            },
            "annotations": annotations("Station Board: Departures", true),
        }),
        json!({
            "name": "station_board_arrivals",
            "title": "Station Board: Arrivals",
            "description": "Get live arrivals for ANY railway station by its EVA number. \
                Mirror of station_board_departures for arriving trains. Get the EVA from \
                get_city_resource(slug, resource='stations'). Read-only.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "eva": {
                        "type": "string",
                        "description": "Station EVA number (digits only) from \
                            get_city_resource(slug, resource='stations'), e.g. '8000105' \
                            (Frankfurt Hbf).",
                    },
                },
                "required": ["eva"],
            },
            "annotations": annotations("Station Board: Arrivals", true),
        }),
        json!({
            "name": "transit_departures",
            "title": "Transit Departures",
            "description": "Get live public-transport departures with real-time delays for a \
                stop. Sourced from GTFS-RT/HVV/VGN. Unlike the static stop list \
                (get_city_resource(slug, resource='transit')), this returns minute-fresh \
                departures including delay for ONE stop. A stop_id is required. Read-only.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "slug": { "type": "string", "description": SLUG_DESCRIPTION },
                    "stop_id": {
                        "type": "string",
                        "description": "Required stop ID to fetch departures for. Discover a \
                            city's stop IDs with get_city_resource(slug, resource='transit') \
                            first. Format: DELFI 'de:<AGS>:<id>' or a numeric gtfs.de stop id. \
                            NOTE: this is NOT the trip_stop_id from station_departures/\
                            station_arrivals, which identifies one stop of one train run.",
                    },
                },
                "required": ["slug"],
            },
            "annotations": annotations("Transit Departures", true),
        }),
        json!({
            "name": "list_cities",
            "title": "List Cities",
            "description": "List all covered cities (slug, federal state, population, \
                coverage). Takes no arguments. Call this first to discover valid city slugs \
                before invoking any city-scoped tool. Read-only.",
            "inputSchema": no_args_schema(),
            "annotations": annotations("List Cities", false),
        }),
        json!({
            "name": "sources",
            "title": "Data Sources",
            "description": "List all data sources with license, attribution and availability. \
                Takes no arguments. Shows which upstream sources Atlas bundles and whether each \
                is currently active. Read-only.",
            "inputSchema": no_args_schema(),
            "annotations": annotations("Data Sources", false),
        }),
        json!({
            "name": "compare",
            "title": "Compare Cities",
            "description": "Compare ONE resource across MULTIPLE cities in a single response. \
                Fans the resource out over the listed cities and returns a per-city \
                source_status (ok/disabled/no_data/error/not_found), so a missing or failing \
                city source does not spoil the whole answer. Read-only.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "description": "Resource to compare. Supported: weather, air, \
                            indicators, demographics, unemployment, tourism, charging-status, \
                            weather-warnings.",
                    },
                    "cities": {
                        "type": "string",
                        "description": "Comma-separated list of city slugs, e.g. \
                            'berlin,koeln,hamburg' (max. 28 cities).",
                    },
                },
                "required": ["resource", "cities"],
            },
            "annotations": annotations("Compare Cities", true),
        }),
    ];

    json!({ "tools": tools })
}

pub async fn call(params: &Value, ctx: &AppContext) -> Result<Value, RpcError> {
    let name = params
        .get("name")
        .and_then(Value::as_str)
        .ok_or_else(|| RpcError::invalid_params("missing tool name"))?;
    let args = params.get("arguments").cloned().unwrap_or(json!({}));
    let client = &ctx.client;
    let ip = ctx.client_ip.as_deref();

    let outcome = match name {
        "get_city" => run(client.get_resource(str_arg(&args, "slug")?, "base", &[], ip).await),
        "get_city_overview" => {
            run(client.get_resource(str_arg(&args, "slug")?, "overview", &[], ip).await)
        }
        "get_city_resource" => {
            let slug = str_arg(&args, "slug")?;
            let resource = str_arg(&args, "resource")?;
            if !crate::atlas_api::generic_resources().contains(&resource) {
                return Err(RpcError::invalid_params(format!(
                    "resource {resource:?} is not a valid data type key"
                )));
            }
            run(client.get_resource(slug, resource, &[], ip).await)
        }
        "air_quality" => run(client.get_resource(str_arg(&args, "slug")?, "air-uba", &[], ip).await),
        "weather" => run(client.get_resource(str_arg(&args, "slug")?, "weather", &[], ip).await),
        "pois" => {
            let slug = str_arg(&args, "slug")?;
            let poi_type = str_arg(&args, "type")?;
            run(client.get_resource(slug, "pois", &[("type", poi_type)], ip).await)
        }
        "station_board_departures" => {
            run(client.get_station_board(str_arg(&args, "eva")?, "departures", ip).await)
        }
        "station_board_arrivals" => {
            run(client.get_station_board(str_arg(&args, "eva")?, "arrivals", ip).await)
        }
        "transit_departures" => return transit_departures(&args, client, ip).await,
        "list_cities" => run(client.get_collection("cities", &[("limit", "200")], ip).await),
        "sources" => run(client.get_collection("sources", &[("limit", "200")], ip).await),
        "compare" => {
            let resource = str_arg(&args, "resource")?;
            let cities = str_arg(&args, "cities")?;
            run(client
                .get_collection("compare", &[("resource", resource), ("cities", cities)], ip)
                .await)
        }
        other => {
            return Err(RpcError {
                code: -32602,
                message: format!("unknown tool: {other}"),
            })
        }
    };

    Ok(tool_result(outcome))
}

fn str_arg<'a>(args: &'a Value, key: &str) -> Result<&'a str, RpcError> {
    args.get(key)
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty())
        .ok_or_else(|| RpcError::invalid_params(format!("missing or empty argument: {key}")))
}

/// The outcome of a tool call before it's wrapped into MCP's CallToolResult
/// shape: either a JSON envelope to return, or a hard error (4xx/protocol
/// failure) that should surface to the model as a real tool error.
enum Outcome {
    Envelope(Value),
    Error(String),
}

fn run(result: Result<Value, UpstreamError>) -> Outcome {
    match result {
        Ok(v) => Outcome::Envelope(v),
        // 5xx (or a request that never reached the API, status None from a
        // transport failure) degrades gracefully into an honest
        // source_status="error" envelope instead of a hard tool failure.
        Err(e) if e.status.map(|s| s >= 500).unwrap_or(true) => {
            Outcome::Envelope(error_envelope("error", &e.message))
        }
        // 4xx and client-side validation failures (bad slug/resource/EVA)
        // surface as a real tool error so the model sees it and can
        // self-correct.
        Err(e) => Outcome::Error(e.message),
    }
}

fn error_envelope(status: &str, note: &str) -> Value {
    json!({ "data": null, "meta": { "source_status": status, "note": note } })
}

fn tool_result(outcome: Outcome) -> Value {
    match outcome {
        Outcome::Envelope(v) => json!({
            "content": [{ "type": "text", "text": v.to_string() }],
            "structuredContent": v,
            "isError": false,
        }),
        Outcome::Error(msg) => json!({
            "content": [{ "type": "text", "text": msg }],
            "isError": true,
        }),
    }
}

async fn transit_departures(
    args: &Value,
    client: &Client,
    ip: Option<&str>,
) -> Result<Value, RpcError> {
    let slug = str_arg(args, "slug")?;
    let stop_id = args.get("stop_id").and_then(Value::as_str).unwrap_or("");

    if stop_id.is_empty() {
        return Ok(tool_result(Outcome::Envelope(error_envelope(
            "no_data",
            "Provide a stop_id to get live departures. Discover valid stop IDs for this city \
            with get_city_resource(slug, resource='transit'), then call again.",
        ))));
    }
    if is_trip_stop_id(stop_id) {
        return Ok(tool_result(Outcome::Envelope(error_envelope(
            "no_data",
            &format!(
                "'{stop_id}' is a trip_stop_id from a station board (station_departures/\
                station_arrivals): it identifies ONE STOP OF ONE TRAIN RUN, not a station. This \
                tool needs a stop ID in the DELFI pattern 'de:<AGS>:<id>' or a numeric gtfs.de \
                stop id. Get one from get_city_resource(slug, resource='transit') (field \
                stop_id), then call again."
            ),
        ))));
    }

    let outcome = run(client
        .get_live(slug, "transit/departures", &[("stop_id", stop_id)], ip)
        .await);
    Ok(tool_result(outcome))
}

/// Matches `<trip>-<YYMMDDHHMM>-<stop index>` (e.g.
/// "9127336349809054555-2607261306-1"), the trip-stop-id format of station
/// board results — NOT a real stop id, but a common mix-up.
fn is_trip_stop_id(s: &str) -> bool {
    let s = s.strip_prefix('-').unwrap_or(s);
    let parts: Vec<&str> = s.split('-').collect();
    parts.len() == 3
        && !parts[0].is_empty()
        && parts[0].chars().all(|c| c.is_ascii_digit())
        && parts[1].len() == 10
        && parts[1].chars().all(|c| c.is_ascii_digit())
        && !parts[2].is_empty()
        && parts[2].chars().all(|c| c.is_ascii_digit())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trip_stop_id_detection() {
        assert!(is_trip_stop_id("9127336349809054555-2607261306-1"));
        assert!(is_trip_stop_id("-7906017824379584014-2607260946-5"));
        assert!(!is_trip_stop_id("de:11000:900000007103"));
        assert!(!is_trip_stop_id("900000007103"));
    }

    #[test]
    fn list_tools_has_all_twelve() {
        let tools = list_tools();
        assert_eq!(tools["tools"].as_array().unwrap().len(), TOOL_COUNT);
    }

    #[test]
    fn get_city_resource_enum_excludes_pois() {
        let tools = list_tools();
        let gcr = tools["tools"]
            .as_array()
            .unwrap()
            .iter()
            .find(|t| t["name"] == "get_city_resource")
            .unwrap();
        let enum_values = gcr["inputSchema"]["properties"]["resource"]["enum"]
            .as_array()
            .unwrap();
        assert!(!enum_values.iter().any(|v| v == "pois"));
    }
}
