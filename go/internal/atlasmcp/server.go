// Package atlasmcp builds the Atlas MCP server: registration of tools,
// resources and prompts on top of the official Go MCP SDK. It mirrors
// src/infranode/mcp/server.py in the Python implementation, which this
// package is replacing. There is no mapping or licensing logic here — every
// tool is a thin, read-only wrapper around the internal Atlas REST API via
// atlasapi.Client.
package atlasmcp

import (
	"context"
	"encoding/json"
	"fmt"
	"sort"

	"github.com/4aia/idkyet/go/internal/atlasapi"
	"github.com/google/jsonschema-go/jsonschema"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const (
	serverName    = "atlas"
	serverVersion = "1.0.0"
)

// New builds the Atlas MCP server: all tools, resources and prompts
// registered, instructions stamped with the live tool/data-type counts.
func New(api *atlasapi.Client) *mcp.Server {
	dataTypeCount := len(atlasapi.AllowedResources) - 1 // "overview" is the meta resource itself

	s := mcp.NewServer(&mcp.Implementation{
		Name:    serverName,
		Title:   "Atlas",
		Version: serverVersion,
	}, &mcp.ServerOptions{
		Instructions: instructions(dataTypeCount, 12),
	})

	registerTools(s, api)
	registerResources(s, api)
	registerPrompts(s)

	return s
}

func instructions(dataTypeCount, toolCount int) string {
	return fmt.Sprintf(
		"Atlas is a keyless, read-only open-data API for 84 German cities with "+
			"~%d data types, exposed as %d MCP tools. To answer ANY city question, "+
			"START with get_city_overview(slug): it returns the city's base data, a "+
			"catalog of ALL available data types (each with its coverage status and "+
			"the exact tool to call next) and a small live snapshot (weather, air, "+
			"train departures). Most data types are fetched with ONE generic tool: "+
			"get_city_resource(slug, resource=<type>), where <type> is the catalog "+
			"key (e.g. 'parking', 'charging', 'demographics', 'solar'); its resource "+
			"enum lists every valid key. City slugs are resolved leniently: you may "+
			"pass the German name with or without umlauts, any casing, a common "+
			"English exonym or a short form (e.g. 'muenchen', 'München', 'munich', "+
			"'munchen', 'cologne', 'frankfurt' all resolve to the canonical slug), "+
			"so you rarely need the exact ASCII slug; an unrecognized name returns a "+
			"404 whose hint names the closest match ('Meintest du ...?'). Discover "+
			"the canonical slugs with list_cities (or the atlas://cities resource); "+
			"browse every data type with the atlas://catalog resource; see sources "+
			"and licenses with sources. Compare one metric across many cities in one "+
			"call with compare. Every tool returns a canonical {data, meta} "+
			"envelope; meta.source_status tells you whether a source delivered data "+
			"(ok / no_data / not_covered / disabled / error), so a missing source "+
			"degrades gracefully instead of failing. Field names are snake_case and "+
			"English across all data types (post_code, street, house_number, place, "+
			"name, start, end, distance_km, power_kw, lat, lon); timestamps carry a "+
			"time zone and a missing value is null, never an empty string. The "+
			"atlas://catalog resource spells the conventions out. Coverage keeps "+
			"growing: more data types and cities are added regularly.",
		dataTypeCount, toolCount,
	)
}

func annotations(title string, openWorld bool) *mcp.ToolAnnotations {
	return &mcp.ToolAnnotations{
		Title:           title,
		ReadOnlyHint:    true,
		DestructiveHint: boolPtr(false),
		IdempotentHint:  true,
		OpenWorldHint:   boolPtr(openWorld),
	}
}

func boolPtr(b bool) *bool { return &b }

func registerTools(s *mcp.Server, api *atlasapi.Client) {
	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_city",
		Description: "Get base data for a German city (population, area, coordinates). Sourced from Wikidata. Read-only. Useful as a first lookup to confirm a city exists and get its core attributes. For a broader question about the city use get_city_overview instead.",
		Annotations: annotations("City Base Data", true),
	}, getCity(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_city_overview",
		Description: "Get a ONE-CALL overview of everything Atlas knows about a German city. Start here for any city question. Returns: the city's base data, a CATALOG of all available data types with coverage status and the exact tool to call next, plus a small live highlights snapshot (current weather, air quality and train departures). Read-only.",
		Annotations: annotations("City Overview", true),
	}, getCityOverview(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_city_resource",
		Description: "Fetch ANY per-city data type by its key (generic accessor). One tool for the whole breadth of Atlas: live data, statistics, multi-year time series, infrastructure and environment data, and more. Discover the valid keys and per-city coverage with get_city_overview(slug) or the atlas://catalog resource; the resource enum lists every key. Uncovered types return source_status=\"not_covered\" (plus where they ARE available), never an error. Read-only.",
		Annotations: annotations("City Data by Type", true),
		InputSchema: genericResourceSchema(),
	}, getCityResource(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "air_quality",
		Description: "Get official air quality for a German city (PM10, NO2 and more). Sourced from the Umweltbundesamt (UBA). Read-only. For live nearest-station hourly readings use get_city_resource(slug, resource='air') instead.",
		Annotations: annotations("Air Quality", true),
	}, airQuality(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "weather",
		Description: "Get current weather observations for a German city. Sourced from the Deutscher Wetterdienst (DWD). Read-only, current conditions only (not a forecast). For warnings use get_city_resource(slug, resource='weather-warnings').",
		Annotations: annotations("Weather", true),
	}, weather(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "pois",
		Description: "Get points of interest in a German city, filtered by type. Sourced from OpenStreetMap. Read-only.",
		Annotations: annotations("Points of Interest", true),
	}, pois(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "station_board_departures",
		Description: "Get live departures for ANY railway station by its EVA number. Covers all train categories including local/regional (S/RB/RE) and long distance, with real-time delays, cancellations and disruption messages. Get the EVA from get_city_resource(slug, resource='stations'). Read-only.",
		Annotations: annotations("Station Board: Departures", true),
	}, stationBoardDepartures(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "station_board_arrivals",
		Description: "Get live arrivals for ANY railway station by its EVA number. Mirror of station_board_departures for arriving trains. Get the EVA from get_city_resource(slug, resource='stations'). Read-only.",
		Annotations: annotations("Station Board: Arrivals", true),
	}, stationBoardArrivals(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "transit_departures",
		Description: "Get live public-transport departures with real-time delays for a stop. Sourced from GTFS-RT/HVV/VGN. Unlike the static stop list (get_city_resource(slug, resource='transit')), this returns minute-fresh departures including delay for ONE stop. A stop_id is required. Read-only.",
		Annotations: annotations("Transit Departures", true),
	}, transitDepartures(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "list_cities",
		Description: "List all covered cities (slug, federal state, population, coverage). Takes no arguments. Call this first to discover valid city slugs before invoking any city-scoped tool. Read-only.",
		Annotations: annotations("List Cities", false),
	}, listCities(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "sources",
		Description: "List all data sources with license, attribution and availability. Takes no arguments. Shows which upstream sources Atlas bundles and whether each is currently active. Read-only.",
		Annotations: annotations("Data Sources", false),
	}, sources(api))

	mcp.AddTool(s, &mcp.Tool{
		Name:        "compare",
		Description: "Compare ONE resource across MULTIPLE cities in a single response. Fans the resource out over the listed cities and returns a per-city source_status (ok/disabled/no_data/error/not_found), so a missing or failing city source does not spoil the whole answer. Read-only.",
		Annotations: annotations("Compare Cities", true),
	}, compare(api))
}

// genericResourceSchema hand-builds the input schema for get_city_resource:
// the "resource" enum is derived at runtime from atlasapi.GenericResources
// (the single source of truth), so it can never drift from what the client
// actually accepts.
func genericResourceSchema() *jsonschema.Schema {
	resourceEnum := make([]any, 0, len(atlasapi.GenericResources()))
	for _, r := range atlasapi.GenericResources() {
		resourceEnum = append(resourceEnum, r)
	}
	return &jsonschema.Schema{
		Type: "object",
		Properties: map[string]*jsonschema.Schema{
			"slug": {
				Type:        "string",
				Description: slugDescription,
			},
			"resource": {
				Type: "string",
				Enum: resourceEnum,
				Description: "Data type key to fetch, exactly as listed by get_city_overview / " +
					"the atlas://catalog resource (the 'type' field), e.g. 'charging', " +
					"'parking', 'demographics', 'solar', 'district-heating'.",
			},
		},
		Required: []string{"slug", "resource"},
	}
}

func registerResources(s *mcp.Server, api *atlasapi.Client) {
	s.AddResource(&mcp.Resource{
		URI:         "atlas://cities",
		Name:        "cities",
		Description: "All covered German cities with slug, federal state, population and coverage.",
		MIMEType:    "application/json",
	}, resourceHandler(func(ctx context.Context) (any, error) {
		return api.GetCollection(ctx, "cities", map[string]string{"limit": "200"})
	}))

	s.AddResource(&mcp.Resource{
		URI:         "atlas://sources",
		Name:        "sources",
		Description: "All Atlas data sources with license, attribution and availability.",
		MIMEType:    "application/json",
	}, resourceHandler(func(ctx context.Context) (any, error) {
		return api.GetCollection(ctx, "sources", map[string]string{"limit": "200"})
	}))

	s.AddResource(&mcp.Resource{
		URI:  "atlas://catalog",
		Name: "catalog",
		Description: "The catalog of all per-city data types: label, matching tool and REST path. " +
			"Lets an agent browse the full breadth of Atlas without a tool call.",
		MIMEType: "application/json",
	}, resourceHandler(func(ctx context.Context) (any, error) {
		return catalogResource(), nil
	}))
}

// resourceHandler adapts a simple (ctx) (any, error) fetcher into an
// mcp.ResourceHandler that returns its result as a JSON text resource.
func resourceHandler(fetch func(ctx context.Context) (any, error)) mcp.ResourceHandler {
	return func(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		data, err := fetch(ctx)
		if err != nil {
			return nil, err
		}
		text, err := jsonText(data)
		if err != nil {
			return nil, err
		}
		return &mcp.ReadResourceResult{
			Contents: []*mcp.ResourceContents{
				{URI: req.Params.URI, MIMEType: "application/json", Text: text},
			},
		}, nil
	}
}

func catalogResource() map[string]any {
	resources := atlasapi.GenericResources()
	dataTypes := make([]map[string]any, 0, len(resources)+1)
	dataTypes = append(dataTypes, map[string]any{
		"type": "base", "tool": "get_city", "path": "/api/v1/cities/{slug}/base",
	})
	dataTypes = append(dataTypes, map[string]any{
		"type": "overview", "tool": "get_city_overview", "path": "/api/v1/cities/{slug}/overview",
	})
	for _, r := range resources {
		if r == "base" || r == "overview" {
			continue
		}
		dataTypes = append(dataTypes, map[string]any{
			"type": r, "tool": "get_city_resource", "path": "/api/v1/cities/{slug}/" + r,
		})
	}
	sort.Slice(dataTypes, func(i, j int) bool {
		return dataTypes[i]["type"].(string) < dataTypes[j]["type"].(string)
	})
	return map[string]any{
		"data_types": dataTypes,
		"note": "Atlas keeps adding more data types and cities. Start with get_city_overview(slug) " +
			"for a live, per-city view. Where 'tool' is get_city_resource, pass the 'type' value as " +
			"its resource argument.",
		"field_conventions": map[string]any{
			"naming": "Fields are snake_case and English across all data types. The same concept " +
				"always uses the same name: post_code, street, house_number, place, name, start, " +
				"end, distance_km, power_kw, lat, lon.",
			"types": "post_code is always a five-character string, so leading zeros survive " +
				"(01067). Coordinates are numbers (lat/lon, WGS84). Timestamps are ISO 8601 and " +
				"always carry a time zone. A value the source does not provide is null, never an " +
				"empty string.",
		},
	}
}

func registerPrompts(s *mcp.Server) {
	s.AddPrompt(&mcp.Prompt{
		Name:        "city_overview",
		Description: "Get a complete picture of a German city and what Atlas offers for it.",
		Arguments:   []*mcp.PromptArgument{{Name: "slug", Required: true}},
	}, promptHandler(func(args map[string]string) string {
		return fmt.Sprintf(
			"Give me an overview of the German city '%s'. Call get_city_overview first to see "+
				"its base data, every available data type (with the tool to fetch each) and a live "+
				"snapshot, then pull the most relevant data types in full and summarize the situation.",
			args["slug"])
	}))

	s.AddPrompt(&mcp.Prompt{
		Name:        "city_briefing",
		Description: "A concise live briefing (weather, air, transit) for a German city.",
		Arguments:   []*mcp.PromptArgument{{Name: "slug", Required: true}},
	}, promptHandler(func(args map[string]string) string {
		return fmt.Sprintf(
			"Give me a concise current briefing for the German city '%s'. Use the Atlas tools to "+
				"fetch weather, air quality and live public-transport departures, then summarize the "+
				"situation in a few bullet points. If a source has no data, say so briefly.",
			args["slug"])
	}))

	s.AddPrompt(&mcp.Prompt{
		Name:        "compare_air_quality",
		Description: "Compare current air quality across several German cities.",
		Arguments:   []*mcp.PromptArgument{{Name: "cities", Required: true}},
	}, promptHandler(func(args map[string]string) string {
		return fmt.Sprintf(
			"Compare the current air quality across these German cities: %s. Use the Atlas "+
				"'compare' tool with resource='air', then rank the cities from cleanest to most "+
				"polluted and note any missing data.",
			args["cities"])
	}))

	s.AddPrompt(&mcp.Prompt{
		Name:        "commute_check",
		Description: "Check the live commute/transit situation for a German city.",
		Arguments:   []*mcp.PromptArgument{{Name: "slug", Required: true}},
	}, promptHandler(func(args map[string]string) string {
		return fmt.Sprintf(
			"Check the live commute situation in the German city '%s': pull real-time "+
				"public-transport departures (transit_departures) and any motorway roadworks/traffic "+
				"(get_city_resource with resource='traffic'), then tell me whether there are notable "+
				"delays right now.",
			args["slug"])
	}))
}

func promptHandler(build func(args map[string]string) string) mcp.PromptHandler {
	return func(_ context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		return &mcp.GetPromptResult{
			Messages: []*mcp.PromptMessage{
				{
					Role:    mcp.Role("user"),
					Content: &mcp.TextContent{Text: build(req.Params.Arguments)},
				},
			},
		}, nil
	}
}

func jsonText(v any) (string, error) {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return "", err
	}
	return string(b), nil
}
