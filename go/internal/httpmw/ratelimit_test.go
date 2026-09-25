package httpmw

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestClientIPPrecedence(t *testing.T) {
	r := httptest.NewRequest(http.MethodGet, "/", nil)
	r.RemoteAddr = "10.0.0.1:1234"
	if got := ClientIP(r); got != "10.0.0.1" {
		t.Errorf("expected peer fallback, got %q", got)
	}

	r.Header.Set("X-Forwarded-For", "198.51.100.9, 10.0.0.2")
	if got := ClientIP(r); got != "198.51.100.9" {
		t.Errorf("expected first XFF hop, got %q", got)
	}

	r.Header.Set("CF-Connecting-IP", "203.0.113.7")
	if got := ClientIP(r); got != "203.0.113.7" {
		t.Errorf("expected CF-Connecting-IP to win, got %q", got)
	}
}

func TestParseAllowlist(t *testing.T) {
	al := parseAllowlist("203.0.113.0/24, 198.51.100.7, not-a-cidr")
	if !al.contains("203.0.113.42") {
		t.Error("expected CIDR entry to match")
	}
	if !al.contains("198.51.100.7") {
		t.Error("expected bare IP to be treated as /32")
	}
	if al.contains("192.0.2.1") {
		t.Error("expected unrelated IP to not match")
	}

	if empty := parseAllowlist(""); empty.contains("203.0.113.1") {
		t.Error("empty allowlist must fail closed (allowlist nobody)")
	}
}

func TestParseRateLimitEnv(t *testing.T) {
	n, w := parseRateLimitEnv("480/minute")
	if n != 480 || w != time.Minute {
		t.Errorf("got n=%d w=%v", n, w)
	}
	n, w = parseRateLimitEnv("garbage")
	if n != defaultLimit || w != defaultWindow {
		t.Errorf("expected fallback to defaults, got n=%d w=%v", n, w)
	}
}

func TestLimiterAllowsUpToLimitThenBlocks(t *testing.T) {
	l := newLimiter(3, time.Minute)
	for i := 0; i < 3; i++ {
		if !l.allow("ip") {
			t.Fatalf("hit %d should have been allowed", i)
		}
	}
	if l.allow("ip") {
		t.Fatal("4th hit within the window should be blocked")
	}
	if !l.allow("other-ip") {
		t.Fatal("a different key must have its own budget")
	}
}

func TestConcurrencyLimit(t *testing.T) {
	release := make(chan struct{})
	started := make(chan struct{}, 2)
	slow := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started <- struct{}{}
		<-release
		w.WriteHeader(http.StatusOK)
	})
	h := ConcurrencyLimit(1, slow)

	go func() {
		req := httptest.NewRequest(http.MethodGet, "/", nil)
		h.ServeHTTP(httptest.NewRecorder(), req)
	}()
	<-started // first request is now in-flight, holding the one slot

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503 while at capacity, got %d", rec.Code)
	}

	close(release)
}
