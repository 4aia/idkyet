// Tool argument structs and handlers. Each handler is a thin wrapper that
// calls atlasapi.Client and returns the normalized JSON envelope unchanged —
// there is no mapping or licensing logic here, mirroring
// src/infranode/mcp/tools.py in the Python implementation.
package atlasmcp

import (
	"context"
	"regexp"

	"github.com/4aia/idkyet/go/internal/atlasapi"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// tripStopIDRe matches the trip-stop-id pattern of station board results
// (<trip>-<YYMMDDHHMM>-<stop index>, e.g. "9127336349809054555-2607261306-1").
// It is NOT a stop id; agents that pass it to transit_departures get a
// corrective note instead of a raw 400, mirroring tools.py.
var tripStopIDRe = regexp.MustCompile(`^-?\d+-\d{10}-\d+$`)

const slugDescription = "City identifier, e.g. 'berlin' or 'hamburg'. Resolved leniently: the " +
	"German name with or without umlauts, any casing, a common English exonym or short form " +
	"also works (München/munich/munchen -> muenchen, cologne -> koeln, frankfurt -> " +
	"frankfurt-am-main). An unknown name returns 404 with a 'Meintest du ...?' suggestion. " +
	"list_cities gives the canonical slugs."

// envelope is what every tool call returns: the REST API's {data, meta}
// JSON, passed straight through. It is typed as `any` on the Out side of
// AddTool so no output schema is generated (deliberate token-footprint
// choice, same rationale as the Python server's schema diet).
type envelope = any

func errorEnvelope(status string, note string) envelope {
	return map[string]any{
		"data": nil,
		"meta": map[string]any{
			"source_status": status,
			"note":          note,
		},
	}
}

// graceful turns a transient 5xx UpstreamError into an honest
// source_status="error" envelope instead of a hard tool failure; 4xx (and
// any other error) is returned as-is so the model sees a real tool error and
// can self-correct.
func graceful(v any, err error) (*mcp.CallToolResult, envelope, error) {
	if err == nil {
		return nil, v, nil
	}
	if upErr, ok := err.(*atlasapi.UpstreamError); ok && upErr.StatusCode >= 500 {
		return nil, errorEnvelope("error", upErr.Error()), nil
	}
	return nil, nil, err
}

type slugArgs struct {
	Slug string `json:"slug" jsonschema:"City identifier, e.g. 'berlin' or 'hamburg'. Resolved leniently (with/without umlauts, any casing, English exonyms). list_cities gives the canonical slugs."`
}

func getCity(api *atlasapi.Client) mcp.ToolHandlerFor[slugArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in slugArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetResource(ctx, in.Slug, "base", nil))
	}
}

func getCityOverview(api *atlasapi.Client) mcp.ToolHandlerFor[slugArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in slugArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetResource(ctx, in.Slug, "overview", nil))
	}
}

func airQuality(api *atlasapi.Client) mcp.ToolHandlerFor[slugArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in slugArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetResource(ctx, in.Slug, "air-uba", nil))
	}
}

func weather(api *atlasapi.Client) mcp.ToolHandlerFor[slugArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in slugArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetResource(ctx, in.Slug, "weather", nil))
	}
}

type getCityResourceArgs struct {
	Slug     string `json:"slug"`
	Resource string `json:"resource"`
}

func getCityResource(api *atlasapi.Client) mcp.ToolHandlerFor[getCityResourceArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in getCityResourceArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetResource(ctx, in.Slug, in.Resource, nil))
	}
}

type poisArgs struct {
	Slug string `json:"slug" jsonschema:"City identifier, e.g. 'berlin' or 'hamburg'."`
	Type string `json:"type" jsonschema:"POI type from the API allowlist, one of: hospital, school, pharmacy, restaurant, police, kindergarten."`
}

func pois(api *atlasapi.Client) mcp.ToolHandlerFor[poisArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in poisArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetResource(ctx, in.Slug, "pois", map[string]string{"type": in.Type}))
	}
}

type stationBoardArgs struct {
	Eva string `json:"eva" jsonschema:"Station EVA number (digits only) from get_city_resource(slug, resource='stations'), e.g. '8011160'."`
}

func stationBoardDepartures(api *atlasapi.Client) mcp.ToolHandlerFor[stationBoardArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in stationBoardArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetStationBoard(ctx, in.Eva, "departures"))
	}
}

func stationBoardArrivals(api *atlasapi.Client) mcp.ToolHandlerFor[stationBoardArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in stationBoardArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetStationBoard(ctx, in.Eva, "arrivals"))
	}
}

type transitDeparturesArgs struct {
	Slug   string `json:"slug" jsonschema:"City identifier, e.g. 'berlin' or 'hamburg'."`
	StopID string `json:"stop_id,omitempty" jsonschema:"Required stop ID. Discover a city's stop IDs with get_city_resource(slug, resource='transit') first. Format: DELFI 'de:<AGS>:<id>' or a numeric gtfs.de stop id. This is NOT the trip_stop_id from station_departures/station_arrivals."`
}

func transitDepartures(api *atlasapi.Client) mcp.ToolHandlerFor[transitDeparturesArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in transitDeparturesArgs) (*mcp.CallToolResult, envelope, error) {
		if in.StopID == "" {
			return nil, errorEnvelope("no_data",
				"Provide a stop_id to get live departures. Discover valid stop IDs for this "+
					"city with get_city_resource(slug, resource='transit'), then call again."), nil
		}
		if tripStopIDRe.MatchString(in.StopID) {
			return nil, errorEnvelope("no_data",
				"'"+in.StopID+"' is a trip_stop_id from a station board (station_departures/"+
					"station_arrivals): it identifies ONE STOP OF ONE TRAIN RUN, not a station. "+
					"This tool needs a stop ID in the DELFI pattern 'de:<AGS>:<id>' or a numeric "+
					"gtfs.de stop id. Get one from get_city_resource(slug, resource='transit') "+
					"(field stop_id), then call again."), nil
		}
		return graceful(api.GetLive(ctx, in.Slug, "transit/departures", map[string]string{"stop_id": in.StopID}))
	}
}

type noArgs struct{}

func listCities(api *atlasapi.Client) mcp.ToolHandlerFor[noArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, _ noArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetCollection(ctx, "cities", map[string]string{"limit": "200"}))
	}
}

func sources(api *atlasapi.Client) mcp.ToolHandlerFor[noArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, _ noArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetCollection(ctx, "sources", map[string]string{"limit": "200"}))
	}
}

type compareArgs struct {
	Resource string `json:"resource" jsonschema:"Resource to compare. Supported: weather, air, indicators, demographics, unemployment, tourism, charging-status, weather-warnings."`
	Cities   string `json:"cities" jsonschema:"Comma-separated list of city slugs, e.g. 'berlin,koeln,hamburg' (max. 28 cities)."`
}

func compare(api *atlasapi.Client) mcp.ToolHandlerFor[compareArgs, envelope] {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in compareArgs) (*mcp.CallToolResult, envelope, error) {
		return graceful(api.GetCollection(ctx, "compare", map[string]string{
			"resource": in.Resource,
			"cities":   in.Cities,
		}))
	}
}
