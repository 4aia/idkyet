// Package httpmw provides HTTP middleware for the remote (streamable-http)
// Atlas MCP endpoint: per-IP rate limiting, a concurrency cap, and real
// client-IP propagation into the request context. It mirrors
// src/infranode/mcp/{ratelimit,clientip}.py in the Python implementation.
//
// Known scaffold gap: the rate limiter here is process-local (an in-memory
// sliding window), unlike the Python version's Redis-backed limiter that
// shares budget across replicas. Fine for a single instance; revisit if this
// is ever scaled horizontally.
package httpmw

import (
	"encoding/json"
	"net"
	"net/http"
	"net/netip"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/4aia/idkyet/go/internal/atlasapi"
)

const (
	allowlistEnvVar = "ratelimitAllowlist"
	rateLimitEnvVar = "mcpRateLimit"
	defaultLimit    = 480
	defaultWindow   = time.Minute
)

// ClientIP returns the real client IP of an inbound request: CF-Connecting-IP
// (set verbindlich by Cloudflare), then X-Forwarded-For's first hop, then the
// TCP peer. Only trustworthy behind the CF-only origin firewall described in
// deploy/harden_firewall.sh — same source as the REST API's real_client_ip.
func ClientIP(r *http.Request) string {
	if cf := r.Header.Get("CF-Connecting-IP"); cf != "" {
		return strings.TrimSpace(cf)
	}
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		return strings.TrimSpace(strings.Split(xff, ",")[0])
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

// allowlist is a fail-safe CIDR bypass list: an empty/unparsable
// configuration allowlists nobody. Bare IPs count as /32 or /128.
type allowlist []netip.Prefix

func parseAllowlist(raw string) allowlist {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	var out allowlist
	for _, part := range strings.Split(raw, ",") {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		if !strings.Contains(part, "/") {
			if addr, err := netip.ParseAddr(part); err == nil {
				bits := 32
				if addr.Is6() {
					bits = 128
				}
				part = addr.String() + "/" + strconv.Itoa(bits)
			}
		}
		if prefix, err := netip.ParsePrefix(part); err == nil {
			out = append(out, prefix)
		}
		// Invalid entries are silently dropped (fail-safe: they never
		// allowlist anything), mirroring infra/allowlist.py.
	}
	return out
}

func (a allowlist) contains(ip string) bool {
	addr, err := netip.ParseAddr(ip)
	if err != nil || len(a) == 0 {
		return false
	}
	for _, prefix := range a {
		if prefix.Contains(addr) {
			return true
		}
	}
	return false
}

// limiter is a per-key sliding-window request counter.
type limiter struct {
	mu     sync.Mutex
	hits   map[string][]time.Time
	limit  int
	window time.Duration
}

func newLimiter(limit int, window time.Duration) *limiter {
	return &limiter{hits: make(map[string][]time.Time), limit: limit, window: window}
}

// allow reports whether a new hit for key is within budget, recording it if so.
func (l *limiter) allow(key string) bool {
	now := time.Now()
	cutoff := now.Add(-l.window)

	l.mu.Lock()
	defer l.mu.Unlock()

	existing := l.hits[key]
	kept := existing[:0]
	for _, t := range existing {
		if t.After(cutoff) {
			kept = append(kept, t)
		}
	}
	if len(kept) >= l.limit {
		l.hits[key] = kept
		return false
	}
	l.hits[key] = append(kept, now)
	return true
}

// parseRateLimitEnv parses the "<N>/<unit>" format used by
// mcpRateLimit (limits-library format on the Python side), e.g.
// "480/minute". Falls back to the default on any parse failure.
func parseRateLimitEnv(raw string) (int, time.Duration) {
	parts := strings.SplitN(raw, "/", 2)
	if len(parts) != 2 {
		return defaultLimit, defaultWindow
	}
	n, err := strconv.Atoi(strings.TrimSpace(parts[0]))
	if err != nil || n <= 0 {
		return defaultLimit, defaultWindow
	}
	var window time.Duration
	switch strings.ToLower(strings.TrimSpace(parts[1])) {
	case "second", "seconds":
		window = time.Second
	case "minute", "minutes":
		window = time.Minute
	case "hour", "hours":
		window = time.Hour
	case "day", "days":
		window = 24 * time.Hour
	default:
		return defaultLimit, defaultWindow
	}
	return n, window
}

// RateLimit rate-limits requests per real client IP (moving window), unless
// the IP is covered by ratelimitAllowlist. On top of that, it
// stashes the client IP in the request context (atlasapi.WithClientIP) so
// downstream tool calls can forward it to the REST API for
// dashboard/alerting provenance (best-effort, not an auth mechanism).
func RateLimit(next http.Handler) http.Handler {
	n, window := parseRateLimitEnv(os.Getenv(rateLimitEnvVar))
	l := newLimiter(n, window)
	allowed := parseAllowlist(os.Getenv(allowlistEnvVar))
	retryAfter := strconv.Itoa(int(window.Seconds()))

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ip := ClientIP(r)
		ctx := atlasapi.WithClientIP(r.Context(), ip)
		r = r.WithContext(ctx)

		if allowed.contains(ip) || l.allow(ip) {
			next.ServeHTTP(w, r)
			return
		}

		w.Header().Set("Retry-After", retryAfter)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusTooManyRequests)
		_ = json.NewEncoder(w).Encode(map[string]string{
			"error":   "rate_limited",
			"message": "MCP rate limit exceeded.",
			"hint":    "Bitte den Retry-After-Header beachten.",
		})
	})
}

// ConcurrencyLimit caps the number of in-flight requests, returning 503 once
// the limit is reached — mirrors uvicorn's limit_concurrency backpressure
// valve for the Python server.
func ConcurrencyLimit(max int, next http.Handler) http.Handler {
	sem := make(chan struct{}, max)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		select {
		case sem <- struct{}{}:
			defer func() { <-sem }()
			next.ServeHTTP(w, r)
		default:
			http.Error(w, "server busy", http.StatusServiceUnavailable)
		}
	})
}
