package atlasapi

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestValidateSlug(t *testing.T) {
	cases := []struct {
		slug    string
		wantErr bool
	}{
		{"berlin", false},
		{"frankfurt-am-main", false},
		{"", true},
		{"berlin/../admin", true},
		{"berlin@evil.example", true},
		{"berlin:8080", true},
		{"berlin admin", true},
		{"berlin?x=1", true},
	}
	for _, c := range cases {
		_, err := validateSlug(c.slug)
		if (err != nil) != c.wantErr {
			t.Errorf("validateSlug(%q): err=%v, wantErr=%v", c.slug, err, c.wantErr)
		}
	}
}

func TestBaseURLAllowlist(t *testing.T) {
	t.Setenv("INFRANODE_MCP_API_BASE", "http://localhost:8000/api/v1")
	if _, err := baseURL(); err != nil {
		t.Fatalf("expected allowlisted host to pass, got: %v", err)
	}

	t.Setenv("INFRANODE_MCP_API_BASE", "http://evil.example/api/v1")
	if _, err := baseURL(); err == nil {
		t.Fatal("expected non-allowlisted host to be rejected")
	}

	t.Setenv("INFRANODE_MCP_API_BASE", "ftp://localhost/api/v1")
	if _, err := baseURL(); err == nil {
		t.Fatal("expected non-http(s) scheme to be rejected")
	}
}

func TestGetResourceRejectsUnknownResource(t *testing.T) {
	t.Setenv("INFRANODE_MCP_API_BASE", "http://localhost:8000/api/v1")
	c, err := New()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := c.GetResource(context.Background(), "berlin", "not-a-real-resource", nil); err == nil {
		t.Fatal("expected unknown resource to be rejected before any request")
	}
}

func TestGetStationBoardValidatesEva(t *testing.T) {
	t.Setenv("INFRANODE_MCP_API_BASE", "http://localhost:8000/api/v1")
	c, err := New()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := c.GetStationBoard(context.Background(), "not-digits", "departures"); err == nil {
		t.Fatal("expected non-numeric EVA to be rejected")
	}
	if _, err := c.GetStationBoard(context.Background(), "12345", "departures"); err == nil {
		t.Fatal("expected too-short EVA to be rejected")
	}
	if _, err := c.GetStationBoard(context.Background(), "8011160", "sideways"); err == nil {
		t.Fatal("expected unknown board to be rejected")
	}
}

func TestGenericResourcesExcludesPois(t *testing.T) {
	for _, r := range GenericResources() {
		if r == "pois" {
			t.Fatal("GenericResources must exclude 'pois' (it has its own tool)")
		}
	}
	if !AllowedResources["pois"] {
		t.Fatal("AllowedResources must still include 'pois' for direct client validation")
	}
}

func TestRequestRoundTripAndGracefulErrorEnvelope(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/cities/berlin/weather":
			if got := r.Header.Get("X-Infranode-Mcp-Client"); got != "203.0.113.5" {
				t.Errorf("expected client-ip header forwarded, got %q", got)
			}
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(map[string]any{
				"data": map[string]any{"city_slug": "berlin"},
				"meta": map[string]any{"source_status": "ok"},
			})
		case "/cities/berlin/base":
			w.WriteHeader(http.StatusInternalServerError)
			_, _ = w.Write([]byte(`{"error":{"message":"boom","hint":"try later"}}`))
		default:
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer srv.Close()

	// httptest server runs on 127.0.0.1, which is allowlisted.
	t.Setenv("INFRANODE_MCP_API_BASE", srv.URL)
	c, err := New()
	if err != nil {
		t.Fatal(err)
	}

	ctx := WithClientIP(context.Background(), "203.0.113.5")
	v, err := c.GetResource(ctx, "berlin", "weather", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	m, ok := v.(map[string]any)
	if !ok || m["meta"] == nil {
		t.Fatalf("unexpected envelope shape: %#v", v)
	}

	_, err = c.GetResource(context.Background(), "berlin", "base", nil)
	if err == nil {
		t.Fatal("expected an UpstreamError for the 500 response")
	}
	upErr, ok := err.(*UpstreamError)
	if !ok {
		t.Fatalf("expected *UpstreamError, got %T", err)
	}
	if upErr.StatusCode != 500 {
		t.Errorf("expected status 500, got %d", upErr.StatusCode)
	}
}
