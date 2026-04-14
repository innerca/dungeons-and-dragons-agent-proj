package server

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/config"
	"github.com/redis/go-redis/v9"
)

func TestNewHTTPServer_Creation(t *testing.T) {
	cfg := &config.Config{
		Server: config.ServerConfig{
			Port: 8080,
		},
		CORS: config.CORSConfig{
			AllowedOrigins: []string{"http://localhost:3000"},
			AllowedMethods: []string{"GET", "POST", "PUT", "DELETE"},
		},
		Redis: config.RedisAuthConfig{
			AuthKeyPrefix: "auth:",
		},
		SSE: config.SSEConfig{
			Timeout: 30000000000, // 30 seconds
		},
	}

	// Create a Redis client (won't connect for this test)
	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})

	// Create server (grpcClient is nil, but that's OK for this test)
	handler := NewHTTPServer(cfg, nil, rdb)
	if handler == nil {
		t.Fatal("Expected HTTP server handler to be created")
	}
}

func TestNewHTTPServer_HealthCheck(t *testing.T) {
	cfg := &config.Config{
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
			Timeout: 30000000000,
		},
	}

	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})

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

func TestNewHTTPServer_PublicRoutes(t *testing.T) {
	cfg := &config.Config{
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
			Timeout: 30000000000,
		},
	}

	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})

	handler := NewHTTPServer(cfg, nil, rdb)

	// Test that /api/v1/auth/register exists (POST)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", nil)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)
	// Should not be 404 (route exists)
	if w.Code == http.StatusNotFound {
		t.Error("Expected /api/v1/auth/register route to exist")
	}

	// Test that /api/v1/auth/login exists (POST)
	req = httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", nil)
	w = httptest.NewRecorder()

	handler.ServeHTTP(w, req)
	if w.Code == http.StatusNotFound {
		t.Error("Expected /api/v1/auth/login route to exist")
	}
}

func TestNewHTTPServer_AuthenticatedRoutes(t *testing.T) {
	cfg := &config.Config{
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
			Timeout: 30000000000,
		},
	}

	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})

	handler := NewHTTPServer(cfg, nil, rdb)

	// Test that authenticated routes require auth
	// /api/v1/player/state should return 401 without token
	req := httptest.NewRequest(http.MethodGet, "/api/v1/player/state", nil)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status %d for unauthenticated request, got %d", http.StatusUnauthorized, w.Code)
	}
}
