package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/redis/go-redis/v9"
)

func TestExtractToken_FromHeader(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Bearer test-token-123")

	token := extractToken(req)
	if token != "test-token-123" {
		t.Errorf("Expected 'test-token-123', got '%s'", token)
	}
}

func TestExtractToken_FromQueryParam(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/test?token=query-token-456", nil)

	token := extractToken(req)
	if token != "query-token-456" {
		t.Errorf("Expected 'query-token-456', got '%s'", token)
	}
}

func TestExtractToken_HeaderPriority(t *testing.T) {
	// Header should take priority over query param
	req := httptest.NewRequest(http.MethodGet, "/test?token=query-token", nil)
	req.Header.Set("Authorization", "Bearer header-token")

	token := extractToken(req)
	if token != "header-token" {
		t.Errorf("Expected 'header-token', got '%s'", token)
	}
}

func TestExtractToken_Empty(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/test", nil)

	token := extractToken(req)
	if token != "" {
		t.Errorf("Expected empty token, got '%s'", token)
	}
}

func TestExtractToken_InvalidHeader(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "InvalidFormat token")

	token := extractToken(req)
	// Should fallback to query param, which is empty
	if token != "" {
		t.Errorf("Expected empty token, got '%s'", token)
	}
}

func TestAuth_MissingToken(t *testing.T) {
	// Create a mock Redis client
	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6379", // Won't connect for this test
	})

	authMiddleware := Auth(rdb, "auth:")
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()

	authMiddleware(handler).ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status %d, got %d", http.StatusUnauthorized, w.Code)
	}
}

func TestAuth_WithTokenButNoRedis(t *testing.T) {
	// This test will fail to connect to Redis, but tests the flow
	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})

	authMiddleware := Auth(rdb, "auth:")
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Bearer some-token")
	w := httptest.NewRecorder()

	authMiddleware(handler).ServeHTTP(w, req)

	// Will get 503 (service unavailable) or 401 depending on Redis connection
	// Just verify it doesn't reach the next handler
	if w.Code == http.StatusOK {
		t.Error("Should not reach next handler without valid auth")
	}
}

func TestCORS_Creation(t *testing.T) {
	// Test that CORS middleware can be created without errors
	allowedOrigins := []string{"http://localhost:3000"}
	allowedMethods := []string{"GET", "POST", "PUT", "DELETE"}

	corsMiddleware := CORS(allowedOrigins, allowedMethods)
	if corsMiddleware == nil {
		t.Error("Expected CORS middleware to be created")
	}

	// Test it can be applied to a handler
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	wrappedHandler := corsMiddleware(handler)
	if wrappedHandler == nil {
		t.Error("Expected wrapped handler")
	}
}
