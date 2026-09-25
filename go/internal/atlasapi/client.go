// Package atlasapi is a thin HTTP client wrapper around the internal Atlas
// REST API. It carries no mapping or licensing logic of its own: every call
// returns the REST API's canonical {data, meta} envelope unchanged. This
// mirrors src/infranode/mcp/client.py in the Python implementation, which
// this package is replacing.
//
// Security posture (same two gates as the Python client):
//
//   - SSRF gate: the base URL comes exclusively from the INFRANODE_MCP_API_BASE
//     env var (default http://localhost:8000/api/v1) and its host is checked
//     against an allowlist before any request is built.
//   - Injection gate: resource/collection/live-resource names are checked
//     against fixed allowlists, and slugs are validated to be a single path
//     segment (no '/', '@', ':', whitespace, '?', '#') and percent-encoded,
//     before they reach a URL.
package atlasapi

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"sort"
	"strings"
	"time"
)

const (
	defaultBaseURL   = "http://localhost:8000/api/v1"
	sourceHeader     = "X-Infranode-Mcp"
	clientHeader     = "X-Infranode-Mcp-Client"
	defaultListLimit = "50"
)

// AllowedHosts is the SSRF allowlist for the REST API base URL's host.
var AllowedHosts = map[string]bool{
	"localhost": true,
	"127.0.0.1": true,
	"::1":       true,
	"api":       true, // internal docker-compose service name
}

// AllowedResources mirrors client.py's ALLOWED_RESOURCES: every per-city
// resource key servable via GET /cities/{slug}/{resource}.
var AllowedResources = toSet([]string{
	"base", "overview", "air", "air-uba", "weather", "pois", "traffic", "transit",
	"parking", "charging", "charging-status", "water-level", "flood", "pollen-uv",
	"fire-danger", "bathing-water", "hospitals-atlas", "station-facilities",
	"demographics", "energy", "geo", "election", "holidays", "health",
	"road-events", "events", "webcams", "power-load", "power-price",
	"weather-warnings", "civil-protection-warnings", "vehicle-registrations",
	"unemployment", "tourism", "construction", "accidents", "crime-stats",
	"fuel-prices", "sharing", "solar", "solar-roofs", "indicators",
	"sustainability", "population-structure", "population-trend",
	"municipal-finance", "labour-market", "integration", "childcare",
	"education-stats", "social-situation", "care", "land-values", "tax-rates",
	"business-registrations", "insolvencies", "station-departures",
	"station-arrivals", "stations", "playgrounds", "drinking-water",
	"public-toilets", "markets", "parcel-lockers", "post-offices", "post-boxes",
	"public-wifi", "recycling-centres", "government-offices", "education",
	"heritage", "tree-cadastre", "population-density", "public-tenders",
	"bike-counts", "district-heating", "office-wait-times", "council-papers",
	"parking-onstreet", "park-and-ride", "mobility-points", "bike-parking",
})

// AllowedStationBoards mirrors ALLOWED_STATION_BOARDS.
var AllowedStationBoards = toSet([]string{"departures", "arrivals"})

// AllowedLiveResources mirrors ALLOWED_LIVE_RESOURCES.
var AllowedLiveResources = toSet([]string{"transit/departures", "parking"})

// AllowedCollections mirrors ALLOWED_COLLECTIONS.
var AllowedCollections = toSet([]string{"cities", "sources", "compare"})

// GenericResources is AllowedResources minus "pois" (which has its own tool
// because it requires the mandatory "type" parameter) — the enum offered by
// the get_city_resource tool's "resource" parameter.
func GenericResources() []string {
	out := make([]string, 0, len(AllowedResources))
	for r := range AllowedResources {
		if r != "pois" {
			out = append(out, r)
		}
	}
	sort.Strings(out)
	return out
}

func toSet(items []string) map[string]bool {
	m := make(map[string]bool, len(items))
	for _, it := range items {
		m[it] = true
	}
	return m
}

var evaRe = regexp.MustCompile(`^\d{6,8}$`)

// forbiddenSlugChars are path/host separators that could redirect a URL
// (T-12-MCP-INJECT); identical set to client.py's _validate_slug.
const forbiddenSlugChars = "/@:\\ \t\n\r?#"

// clientIPKey is the context key used to carry the real client IP of an
// inbound remote MCP request through to the outgoing loopback call, so it
// can be forwarded via the X-Infranode-Mcp-Client header (best-effort
// provenance for the API's dashboard/alerting, not an auth mechanism).
type clientIPKey struct{}

// WithClientIP returns a context carrying the given client IP.
func WithClientIP(ctx context.Context, ip string) context.Context {
	return context.WithValue(ctx, clientIPKey{}, ip)
}

func clientIPFromContext(ctx context.Context) string {
	ip, _ := ctx.Value(clientIPKey{}).(string)
	return ip
}

// UpstreamError is a readable error built from the REST API's error
// envelope. StatusCode lets callers decide whether to degrade gracefully
// (5xx, transient upstream failure) or surface the error so the model can
// self-correct (4xx, e.g. unknown slug).
type UpstreamError struct {
	StatusCode int
	msg        string
}

func (e *UpstreamError) Error() string { return e.msg }

// Client is a pooled HTTP client for the internal Atlas REST API.
type Client struct {
	httpClient *http.Client
	baseURL    string
}

// New builds a Client, validating the configured base URL's host against
// AllowedHosts up front (fail fast on misconfiguration rather than on the
// first tool call).
func New() (*Client, error) {
	base, err := baseURL()
	if err != nil {
		return nil, err
	}
	return &Client{
		baseURL: base,
		httpClient: &http.Client{
			// Overall per-call cap (matches the Python client's fixed 30s
			// read timeout); connect/keep-alive tuning lives on Transport.
			Timeout: 30 * time.Second,
			Transport: &http.Transport{
				MaxConnsPerHost:     100,
				MaxIdleConnsPerHost: 20,
			},
		},
	}, nil
}

func baseURL() (string, error) {
	raw := os.Getenv("INFRANODE_MCP_API_BASE")
	if raw == "" {
		raw = defaultBaseURL
	}
	u, err := url.Parse(raw)
	if err != nil {
		return "", fmt.Errorf("invalid INFRANODE_MCP_API_BASE %q: %w", raw, err)
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return "", fmt.Errorf("invalid scheme for INFRANODE_MCP_API_BASE: %q, only http/https allowed", u.Scheme)
	}
	if !AllowedHosts[u.Hostname()] {
		hosts := make([]string, 0, len(AllowedHosts))
		for h := range AllowedHosts {
			hosts = append(hosts, h)
		}
		sort.Strings(hosts)
		return "", fmt.Errorf("host %q is not allowlisted (T-12-MCP-SSRF); allowed: %s", u.Hostname(), strings.Join(hosts, ", "))
	}
	return strings.TrimRight(raw, "/"), nil
}

func validateSlug(slug string) (string, error) {
	if slug == "" {
		return "", fmt.Errorf("slug must be a non-empty string")
	}
	if strings.ContainsAny(slug, forbiddenSlugChars) {
		return "", fmt.Errorf("invalid slug %q: contains disallowed characters (path/host separators)", slug)
	}
	return url.PathEscape(slug), nil
}

func withDefaultLimit(params map[string]string) map[string]string {
	merged := make(map[string]string, len(params)+1)
	for k, v := range params {
		merged[k] = v
	}
	if _, hasLimit := merged["limit"]; !hasLimit {
		if _, hasAll := merged["all"]; !hasAll {
			merged["limit"] = defaultListLimit
		}
	}
	return merged
}

// GetResource calls GET /cities/{slug}/{resource} and returns the parsed
// JSON envelope unchanged.
func (c *Client) GetResource(ctx context.Context, slug, resource string, params map[string]string) (any, error) {
	if !AllowedResources[resource] {
		return nil, fmt.Errorf("unknown resource %q (T-12-MCP-INJECT)", resource)
	}
	safeSlug, err := validateSlug(slug)
	if err != nil {
		return nil, err
	}
	path := fmt.Sprintf("/cities/%s/%s", safeSlug, resource)
	return c.request(ctx, path, withDefaultLimit(params), resource)
}

// GetLive calls GET /live/{slug}/{liveResource}.
func (c *Client) GetLive(ctx context.Context, slug, liveResource string, params map[string]string) (any, error) {
	if !AllowedLiveResources[liveResource] {
		return nil, fmt.Errorf("unknown live resource %q (T-12-MCP-INJECT)", liveResource)
	}
	safeSlug, err := validateSlug(slug)
	if err != nil {
		return nil, err
	}
	path := fmt.Sprintf("/live/%s/%s", safeSlug, liveResource)
	return c.request(ctx, path, params, "live:"+liveResource)
}

// GetCollection calls a slug-less GET /{name} endpoint (cities, sources,
// compare).
func (c *Client) GetCollection(ctx context.Context, name string, params map[string]string) (any, error) {
	if !AllowedCollections[name] {
		return nil, fmt.Errorf("unknown collection endpoint %q (T-12-MCP-INJECT)", name)
	}
	return c.request(ctx, "/"+name, params, "collection:"+name)
}

// GetStationBoard calls GET /stations/{eva}/{board} (departures/arrivals).
func (c *Client) GetStationBoard(ctx context.Context, eva, board string) (any, error) {
	if !AllowedStationBoards[board] {
		return nil, fmt.Errorf("unknown board %q (T-12-MCP-INJECT)", board)
	}
	if !evaRe.MatchString(eva) {
		return nil, fmt.Errorf("invalid EVA %q (T-12-MCP-INJECT): expected a 6-8 digit number", eva)
	}
	path := fmt.Sprintf("/stations/%s/%s", eva, board)
	return c.request(ctx, path, nil, "station:"+board)
}

func (c *Client) request(ctx context.Context, path string, params map[string]string, tag string) (any, error) {
	full := c.baseURL + path
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, full, nil)
	if err != nil {
		return nil, err
	}
	if len(params) > 0 {
		q := req.URL.Query()
		for k, v := range params {
			q.Set(k, v)
		}
		req.URL.RawQuery = q.Encode()
	}
	req.Header.Set(sourceHeader, tag)
	if ip := clientIPFromContext(ctx); ip != "" {
		req.Header.Set(clientHeader, ip)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode >= 400 {
		return nil, buildUpstreamError(resp.StatusCode, body)
	}

	var out any
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, fmt.Errorf("atlas API returned non-JSON response: %w", err)
	}
	return out, nil
}

func buildUpstreamError(status int, body []byte) *UpstreamError {
	detail := ""
	var parsed struct {
		Error struct {
			Message string `json:"message"`
			Hint    string `json:"hint"`
		} `json:"error"`
	}
	if json.Unmarshal(body, &parsed) == nil && parsed.Error.Message != "" {
		detail = strings.TrimSpace(parsed.Error.Message + " " + parsed.Error.Hint)
	}
	if detail == "" {
		text := strings.TrimSpace(string(body))
		if len(text) > 200 {
			text = text[:200]
		}
		if text == "" {
			text = http.StatusText(status)
		}
		detail = text
	}
	return &UpstreamError{
		StatusCode: status,
		msg:        fmt.Sprintf("Atlas API %d: %s", status, detail),
	}
}
