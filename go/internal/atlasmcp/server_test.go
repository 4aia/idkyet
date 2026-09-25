package atlasmcp

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/4aia/idkyet/go/internal/atlasapi"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// connect spins up a mock REST API and an in-process client<->server pair
// (mcp.NewInMemoryTransports), so tool calls exercise the real handler and
// schema-validation path without any network or a running Python API.
func connect(t *testing.T, mux *http.ServeMux) *mcp.ClientSession {
	t.Helper()
	srv := httptest.NewServer(mux)
	t.Cleanup(srv.Close)
	t.Setenv("mcpApiBase", srv.URL)

	api, err := atlasapi.New()
	if err != nil {
		t.Fatal(err)
	}
	server := New(api)

	clientTransport, serverTransport := mcp.NewInMemoryTransports()
	if _, err := server.Connect(context.Background(), serverTransport, nil); err != nil {
		t.Fatalf("server connect: %v", err)
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "0.0.0"}, nil)
	session, err := client.Connect(context.Background(), clientTransport, nil)
	if err != nil {
		t.Fatalf("client connect: %v", err)
	}
	t.Cleanup(func() { _ = session.Close() })
	return session
}

func TestListToolsRegistersAllTwelve(t *testing.T) {
	session := connect(t, http.NewServeMux())
	res, err := session.ListTools(context.Background(), nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(res.Tools) != 12 {
		names := make([]string, len(res.Tools))
		for i, tl := range res.Tools {
			names[i] = tl.Name
		}
		t.Fatalf("expected 12 tools, got %d: %v", len(res.Tools), names)
	}
}

func TestGetCityResourceRoundTrip(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/cities/berlin/demographics", func(w http.ResponseWriter, r *http.Request) {
		if got := r.URL.Query().Get("limit"); got != "50" {
			t.Errorf("expected default limit=50 to be applied, got %q", got)
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"data": map[string]any{"city_slug": "berlin"},
			"meta": map[string]any{"source_status": "ok"},
		})
	})
	session := connect(t, mux)

	res, err := session.CallTool(context.Background(), &mcp.CallToolParams{
		Name:      "get_city_resource",
		Arguments: map[string]any{"slug": "berlin", "resource": "demographics"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if res.IsError {
		t.Fatalf("unexpected tool error: %+v", res.Content)
	}
}

func TestGetCityResourceRejectsUnknownEnumValue(t *testing.T) {
	session := connect(t, http.NewServeMux())
	res, err := session.CallTool(context.Background(), &mcp.CallToolParams{
		Name:      "get_city_resource",
		Arguments: map[string]any{"slug": "berlin", "resource": "not-a-real-type"},
	})
	if err != nil {
		t.Fatal(err)
	}
	// An invalid resource surfaces as a tool error (IsError), whether caught
	// by the input schema's enum or by the atlasapi allowlist behind it —
	// either way it must never reach an upstream request.
	if !res.IsError {
		t.Fatal("expected a resource value outside the enum to be rejected as a tool error")
	}
}

func TestTransitDeparturesRequiresStopID(t *testing.T) {
	session := connect(t, http.NewServeMux())
	res, err := session.CallTool(context.Background(), &mcp.CallToolParams{
		Name:      "transit_departures",
		Arguments: map[string]any{"slug": "berlin"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if res.IsError {
		t.Fatalf("missing stop_id should be a self-correcting envelope, not a tool error: %+v", res.Content)
	}
	text, ok := res.Content[0].(*mcp.TextContent)
	if !ok || !strings.Contains(text.Text, "no_data") {
		t.Fatalf("expected a no_data envelope, got: %+v", res.Content)
	}
}

func TestReadCatalogResource(t *testing.T) {
	session := connect(t, http.NewServeMux())
	res, err := session.ReadResource(context.Background(), &mcp.ReadResourceParams{URI: "atlas://catalog"})
	if err != nil {
		t.Fatal(err)
	}
	if len(res.Contents) != 1 || res.Contents[0].Text == "" {
		t.Fatalf("expected non-empty catalog JSON, got: %+v", res.Contents)
	}
	var parsed struct {
		DataTypes []map[string]any `json:"data_types"`
	}
	if err := json.Unmarshal([]byte(res.Contents[0].Text), &parsed); err != nil {
		t.Fatal(err)
	}
	if len(parsed.DataTypes) < 80 {
		t.Errorf("expected the full data-type catalog, got %d entries", len(parsed.DataTypes))
	}
}

func TestGetPrompt(t *testing.T) {
	session := connect(t, http.NewServeMux())
	res, err := session.GetPrompt(context.Background(), &mcp.GetPromptParams{
		Name:      "city_briefing",
		Arguments: map[string]string{"slug": "koeln"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(res.Messages) != 1 {
		t.Fatalf("expected one prompt message, got %d", len(res.Messages))
	}
	text, ok := res.Messages[0].Content.(*mcp.TextContent)
	if !ok || !strings.Contains(text.Text, "koeln") {
		t.Fatalf("expected the slug to be interpolated into the prompt, got: %+v", res.Messages[0].Content)
	}
}
