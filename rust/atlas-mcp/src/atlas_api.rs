//! Thin HTTP client wrapper around the internal Atlas REST API. Carries no
//! mapping or licensing logic: every call returns the REST API's canonical
//! `{data, meta}` envelope unchanged. This mirrors the (now-retired) Go and
//! Python implementations of the same client.
//!
//! Security posture:
//! - Injection gate: resource/collection/live-resource names are checked
//!   against fixed allowlists, and slugs are validated to be a single path
//!   segment (no '/', '@', ':', whitespace, '?', '#') before they reach a URL.
//! - The base URL comes exclusively from the `ATLAS_API_BASE` Worker var,
//!   never from a tool argument, so a request can never be redirected by
//!   client input (no SSRF surface).

use serde_json::Value;
use worker::{Env, Fetch, Headers, Method, Request, RequestInit, Result as WorkerResult, Url};

pub const ALLOWED_RESOURCES: &[&str] = &[
    "base",
    "overview",
    "air",
    "air-uba",
    "weather",
    "pois",
    "traffic",
    "transit",
    "parking",
    "charging",
    "charging-status",
    "water-level",
    "flood",
    "pollen-uv",
    "fire-danger",
    "bathing-water",
    "hospitals-atlas",
    "station-facilities",
    "demographics",
    "energy",
    "geo",
    "election",
    "holidays",
    "health",
    "road-events",
    "events",
    "webcams",
    "power-load",
    "power-price",
    "weather-warnings",
    "civil-protection-warnings",
    "vehicle-registrations",
    "unemployment",
    "tourism",
    "construction",
    "accidents",
    "crime-stats",
    "fuel-prices",
    "sharing",
    "solar",
    "solar-roofs",
    "indicators",
    "sustainability",
    "population-structure",
    "population-trend",
    "municipal-finance",
    "labour-market",
    "integration",
    "childcare",
    "education-stats",
    "social-situation",
    "care",
    "land-values",
    "tax-rates",
    "business-registrations",
    "insolvencies",
    "station-departures",
    "station-arrivals",
    "stations",
    "playgrounds",
    "drinking-water",
    "public-toilets",
    "markets",
    "parcel-lockers",
    "post-offices",
    "post-boxes",
    "public-wifi",
    "recycling-centres",
    "government-offices",
    "education",
    "heritage",
    "tree-cadastre",
    "population-density",
    "public-tenders",
    "bike-counts",
    "district-heating",
    "office-wait-times",
    "council-papers",
    "parking-onstreet",
    "park-and-ride",
    "mobility-points",
    "bike-parking",
];

pub const ALLOWED_STATION_BOARDS: &[&str] = &["departures", "arrivals"];
pub const ALLOWED_LIVE_RESOURCES: &[&str] = &["transit/departures", "parking"];
pub const ALLOWED_COLLECTIONS: &[&str] = &["cities", "sources", "compare"];

/// `ALLOWED_RESOURCES` minus "pois" (which has its own tool because it needs
/// the mandatory "type" parameter) — the enum offered by get_city_resource.
pub fn generic_resources() -> Vec<&'static str> {
    let mut v: Vec<&'static str> = ALLOWED_RESOURCES
        .iter()
        .copied()
        .filter(|r| *r != "pois")
        .collect();
    v.sort_unstable();
    v
}

const FORBIDDEN_SLUG_CHARS: &[char] = &['/', '@', ':', '\\', ' ', '\t', '\n', '\r', '?', '#'];

pub fn validate_slug(slug: &str) -> Result<String, String> {
    if slug.is_empty() {
        return Err("slug must be a non-empty string".into());
    }
    if slug.chars().any(|c| FORBIDDEN_SLUG_CHARS.contains(&c)) {
        return Err(format!(
            "invalid slug {slug:?}: contains disallowed characters (path/host separators)"
        ));
    }
    Ok(urlencode(slug))
}

fn urlencode(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for b in s.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(b as char)
            }
            _ => out.push_str(&format!("%{b:02X}")),
        }
    }
    out
}

fn is_valid_eva(eva: &str) -> bool {
    (6..=8).contains(&eva.len()) && eva.chars().all(|c| c.is_ascii_digit())
}

/// A readable error built from the REST API's error envelope, carrying the
/// HTTP status so callers can decide whether to degrade gracefully (5xx,
/// transient upstream failure) or surface the error so the model can
/// self-correct (4xx, e.g. unknown slug). `None` status = a client-side
/// rejection that never reached the API (bad slug/resource/EVA).
#[derive(Debug)]
pub struct UpstreamError {
    pub status: Option<u16>,
    pub message: String,
}

impl UpstreamError {
    fn client(message: impl Into<String>) -> Self {
        Self {
            status: None,
            message: message.into(),
        }
    }
}

pub struct Client {
    base_url: String,
}

impl Client {
    pub fn new(env: &Env) -> WorkerResult<Self> {
        let base_url = env
            .var("ATLAS_API_BASE")
            .map(|v| v.to_string())
            .unwrap_or_else(|_| "http://localhost:8000/api/v1".to_string());
        Ok(Self {
            base_url: base_url.trim_end_matches('/').to_string(),
        })
    }

    pub async fn get_resource(
        &self,
        slug: &str,
        resource: &str,
        params: &[(&str, &str)],
        client_ip: Option<&str>,
    ) -> Result<Value, UpstreamError> {
        if !ALLOWED_RESOURCES.contains(&resource) {
            return Err(UpstreamError::client(format!(
                "unknown resource {resource:?}"
            )));
        }
        let safe_slug =
            validate_slug(slug).map_err(UpstreamError::client)?;
        let path = format!("/cities/{safe_slug}/{resource}");
        self.request(&path, &with_default_limit(params), resource, client_ip)
            .await
    }

    pub async fn get_live(
        &self,
        slug: &str,
        live_resource: &str,
        params: &[(&str, &str)],
        client_ip: Option<&str>,
    ) -> Result<Value, UpstreamError> {
        if !ALLOWED_LIVE_RESOURCES.contains(&live_resource) {
            return Err(UpstreamError::client(format!(
                "unknown live resource {live_resource:?}"
            )));
        }
        let safe_slug =
            validate_slug(slug).map_err(UpstreamError::client)?;
        let path = format!("/live/{safe_slug}/{live_resource}");
        self.request(&path, params, &format!("live:{live_resource}"), client_ip)
            .await
    }

    pub async fn get_collection(
        &self,
        name: &str,
        params: &[(&str, &str)],
        client_ip: Option<&str>,
    ) -> Result<Value, UpstreamError> {
        if !ALLOWED_COLLECTIONS.contains(&name) {
            return Err(UpstreamError::client(format!(
                "unknown collection endpoint {name:?}"
            )));
        }
        let path = format!("/{name}");
        self.request(&path, params, &format!("collection:{name}"), client_ip)
            .await
    }

    pub async fn get_station_board(
        &self,
        eva: &str,
        board: &str,
        client_ip: Option<&str>,
    ) -> Result<Value, UpstreamError> {
        if !ALLOWED_STATION_BOARDS.contains(&board) {
            return Err(UpstreamError::client(format!("unknown board {board:?}")));
        }
        if !is_valid_eva(eva) {
            return Err(UpstreamError::client(format!(
                "invalid EVA {eva:?}: expected a 6-8 digit number"
            )));
        }
        let path = format!("/stations/{eva}/{board}");
        self.request(&path, &[], &format!("station:{board}"), client_ip)
            .await
    }

    async fn request(
        &self,
        path: &str,
        params: &[(&str, &str)],
        tag: &str,
        client_ip: Option<&str>,
    ) -> Result<Value, UpstreamError> {
        let mut url = Url::parse(&format!("{}{}", self.base_url, path))
            .map_err(|e| UpstreamError::client(format!("invalid upstream URL: {e}")))?;
        {
            let mut qp = url.query_pairs_mut();
            for (k, v) in params {
                qp.append_pair(k, v);
            }
        }

        let headers = Headers::new();
        headers
            .set("X-Atlas-Mcp", tag)
            .map_err(|e| UpstreamError::client(e.to_string()))?;
        if let Some(ip) = client_ip {
            headers
                .set("X-Atlas-Mcp-Client", ip)
                .map_err(|e| UpstreamError::client(e.to_string()))?;
        }

        let mut init = RequestInit::new();
        init.with_method(Method::Get).with_headers(headers);
        let req = Request::new_with_init(url.as_str(), &init)
            .map_err(|e| UpstreamError::client(e.to_string()))?;

        let mut resp = Fetch::Request(req)
            .send()
            .await
            .map_err(|e| UpstreamError {
                status: Some(502),
                message: format!("upstream request failed: {e}"),
            })?;

        let status = resp.status_code();
        let body: Value = resp.json().await.unwrap_or(Value::Null);

        if status >= 400 {
            let detail = body
                .get("error")
                .and_then(|e| e.get("message"))
                .and_then(|m| m.as_str())
                .unwrap_or("upstream error")
                .to_string();
            return Err(UpstreamError {
                status: Some(status),
                message: format!("Atlas API {status}: {detail}"),
            });
        }
        Ok(body)
    }
}

fn with_default_limit<'a>(params: &[(&'a str, &'a str)]) -> Vec<(&'a str, &'a str)> {
    let has_limit = params.iter().any(|(k, _)| *k == "limit");
    let has_all = params.iter().any(|(k, _)| *k == "all");
    let mut merged: Vec<(&str, &str)> = params.to_vec();
    if !has_limit && !has_all {
        merged.push(("limit", "50"));
    }
    merged
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_slug_accepts_normal_names() {
        assert!(validate_slug("berlin").is_ok());
        assert!(validate_slug("frankfurt-am-main").is_ok());
    }

    #[test]
    fn validate_slug_rejects_path_and_host_separators() {
        assert!(validate_slug("").is_err());
        assert!(validate_slug("berlin/../admin").is_err());
        assert!(validate_slug("berlin@evil.example").is_err());
        assert!(validate_slug("berlin:8080").is_err());
        assert!(validate_slug("berlin admin").is_err());
        assert!(validate_slug("berlin?x=1").is_err());
    }

    #[test]
    fn eva_validation() {
        assert!(is_valid_eva("8011160"));
        assert!(!is_valid_eva("12345"));
        assert!(!is_valid_eva("not-digits"));
        assert!(!is_valid_eva("123456789012"));
    }

    #[test]
    fn generic_resources_excludes_pois_but_allowed_resources_keeps_it() {
        assert!(!generic_resources().contains(&"pois"));
        assert!(ALLOWED_RESOURCES.contains(&"pois"));
    }

    #[test]
    fn default_limit_applied_unless_already_present() {
        assert_eq!(with_default_limit(&[]), vec![("limit", "50")]);
        assert_eq!(
            with_default_limit(&[("limit", "10")]),
            vec![("limit", "10")]
        );
        assert_eq!(with_default_limit(&[("all", "1")]), vec![("all", "1")]);
    }
}
