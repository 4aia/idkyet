//! The four ready-made MCP prompts that showcase common multi-tool flows.

use serde_json::{json, Value};

use crate::mcp::RpcError;

pub fn list_prompts() -> Value {
    json!({
        "prompts": [
            {
                "name": "city_overview",
                "description": "Get a complete picture of a German city and what Atlas offers \
                    for it.",
                "arguments": [{ "name": "slug", "required": true }],
            },
            {
                "name": "city_briefing",
                "description": "A concise live briefing (weather, air, transit) for a German \
                    city.",
                "arguments": [{ "name": "slug", "required": true }],
            },
            {
                "name": "compare_air_quality",
                "description": "Compare current air quality across several German cities.",
                "arguments": [{ "name": "cities", "required": true }],
            },
            {
                "name": "commute_check",
                "description": "Check the live commute/transit situation for a German city.",
                "arguments": [{ "name": "slug", "required": true }],
            },
        ]
    })
}

pub fn get_prompt(params: &Value) -> Result<Value, RpcError> {
    let name = params
        .get("name")
        .and_then(Value::as_str)
        .ok_or_else(|| RpcError::invalid_params("missing prompt name"))?;
    let args = params.get("arguments").cloned().unwrap_or(json!({}));
    let arg = |key: &str| args.get(key).and_then(Value::as_str).unwrap_or("").to_string();

    let text = match name {
        "city_overview" => format!(
            "Give me an overview of the German city '{}'. Call get_city_overview first to see \
            its base data, every available data type (with the tool to fetch each) and a live \
            snapshot, then pull the most relevant data types in full and summarize the \
            situation.",
            arg("slug")
        ),
        "city_briefing" => format!(
            "Give me a concise current briefing for the German city '{}'. Use the Atlas tools \
            to fetch weather, air quality and live public-transport departures, then summarize \
            the situation in a few bullet points. If a source has no data, say so briefly.",
            arg("slug")
        ),
        "compare_air_quality" => format!(
            "Compare the current air quality across these German cities: {}. Use the Atlas \
            'compare' tool with resource='air', then rank the cities from cleanest to most \
            polluted and note any missing data.",
            arg("cities")
        ),
        "commute_check" => format!(
            "Check the live commute situation in the German city '{}': pull real-time \
            public-transport departures (transit_departures) and any motorway roadworks/traffic \
            (get_city_resource with resource='traffic'), then tell me whether there are notable \
            delays right now.",
            arg("slug")
        ),
        other => {
            return Err(RpcError {
                code: -32002,
                message: format!("prompt not found: {other}"),
            })
        }
    };

    Ok(json!({
        "messages": [{ "role": "user", "content": { "type": "text", "text": text } }]
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn interpolates_argument_into_prompt_text() {
        let result = get_prompt(&json!({ "name": "city_briefing", "arguments": { "slug": "koeln" } }))
            .unwrap();
        let text = result["messages"][0]["content"]["text"].as_str().unwrap();
        assert!(text.contains("koeln"));
    }

    #[test]
    fn unknown_prompt_errors() {
        assert!(get_prompt(&json!({ "name": "nope" })).is_err());
    }
}
