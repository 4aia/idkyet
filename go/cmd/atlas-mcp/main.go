// Command atlas-mcp is the Atlas MCP server: a thin, read-only wrapper
// around the internal Atlas REST API, exposed to AI agents over MCP. It
// replaces the Python implementation at src/infranode/mcp/server.py.
//
// Transport is chosen via mcpTransport:
//   - "stdio" (default): local subprocess, no open port.
//   - "streamable-http": public remote endpoint (e.g. mcp.woof.systems),
//     bound to mcpHost:mcpPort behind Caddy/Cloudflare,
//     keyless like the REST API.
package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/4aia/idkyet/go/internal/atlasapi"
	"github.com/4aia/idkyet/go/internal/atlasmcp"
	"github.com/4aia/idkyet/go/internal/httpmw"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const defaultConcurrencyLimit = 256

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	api, err := atlasapi.New()
	if err != nil {
		logger.Error("failed to configure Atlas API client", "error", err)
		os.Exit(1)
	}

	server := atlasmcp.New(api)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	transport := os.Getenv("mcpTransport")
	if transport == "" {
		transport = "stdio"
	}

	switch transport {
	case "streamable-http":
		runStreamableHTTP(ctx, logger, server)
	default:
		if err := server.Run(ctx, &mcp.StdioTransport{}); err != nil {
			logger.Error("server failed", "error", err)
			os.Exit(1)
		}
	}
}

func runStreamableHTTP(ctx context.Context, logger *slog.Logger, server *mcp.Server) {
	host := os.Getenv("mcpHost")
	if host == "" {
		host = "127.0.0.1"
	}
	port := os.Getenv("mcpPort")
	if port == "" {
		port = "8081"
	}

	handler := mcp.NewStreamableHTTPHandler(
		func(*http.Request) *mcp.Server { return server },
		&mcp.StreamableHTTPOptions{Logger: logger},
	)

	var h http.Handler = handler
	h = httpmw.RateLimit(h)
	h = httpmw.ConcurrencyLimit(defaultConcurrencyLimit, h)

	httpServer := &http.Server{
		Addr:              host + ":" + port,
		Handler:           h,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       5 * time.Second,
	}

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = httpServer.Shutdown(shutdownCtx)
	}()

	logger.Info("atlas-mcp listening", "addr", httpServer.Addr)
	if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logger.Error("http server failed", "error", err)
		os.Exit(1)
	}
}
