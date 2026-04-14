package server

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/config"
	"github.com/redis/go-redis/v9"
)

// Helper function to create test config
func testConfig() *config.Config {
	return &config.Config{
		Server: config.ServerConfig{
			Port: 8080,
		},
		CORS: config.CORSConfig{
			AllowedOrigins: []string{"http://localhost:3000"},
			AllowedMethods: []string{"GET", "POST"},
		},
		Redis: config.RedisAuthConfig{
			AuthKeyPrefix: "auth:",
		},
		SSE: config.SSEConfig{
			Timeout: 30 * time.Second,
		},
	}
}

func TestNewHTTPServer_Creation(t *testing.T) {
	cfg := testConfig()
	rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})

	handler := NewHTTPServer(cfg, nil, rdb)
	if handler == nil {
		t.Fatal("Expected HTTP server handler to be created")
	}
}

func TestNewHTTPServer_HealthCheck(t *testing.T) {
	cfg := testConfig()
	rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
	handler := NewHTTPServer(cfg, nil, rdb)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status %d, got %d", http.StatusOK, w.Code)
	}

	expectedBody := `{"status":"ok"}`
	if w.Body.String() != expectedBody {
		t.Errorf("Expected body '%s', got '%s'", expectedBody, w.Body.String())
	}
}

func TestNewHTTPServer_Routes(t *testing.T) {
	cfg := testConfig()
	rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
	handler := NewHTTPServer(cfg, nil, rdb)

	tests := []struct {
		name           string
		method         string
		path           string
		expectNotFound bool
		expectAuth     bool
	}{
		// Public routes
		{name: "register", method: http.MethodPost, path: "/api/v1/auth/register", expectNotFound: false},
		{name: "login", method: http.MethodPost, path: "/api/v1/auth/login", expectNotFound: false},
		{name: "health", method: http.MethodGet, path: "/health", expectNotFound: false},
		
		// Authenticated routes (should return 401 without token)
		{name: "player state without auth", method: http.MethodGet, path: "/api/v1/player/state", expectAuth: true},
		{name: "create character without auth", method: http.MethodPost, path: "/api/v1/character", expectAuth: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(tt.method, tt.path, nil)
			w := httptest.NewRecorder()

			handler.ServeHTTP(w, req)

			if tt.expectAuth {
				if w.Code != http.StatusUnauthorized {
					t.Errorf("Expected status %d, got %d", http.StatusUnauthorized, w.Code)
				}
			} else if tt.expectNotFound {
				if w.Code == http.StatusNotFound {
					t.Error("Expected route to exist")
				}
			}
		})
	}
}
