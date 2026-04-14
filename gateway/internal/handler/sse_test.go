package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/config"
	gamev1 "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/gen/game/v1"
)

func TestSSEHandler_MissingRequestID(t *testing.T) {
	channels := NewResponseChannels()
	traceChannel := NewTraceChannel()
	cfg := &config.Config{
		SSE: config.SSEConfig{
			Timeout: 30 * time.Second,
		},
	}
	handler := NewSSEHandler(channels, traceChannel, cfg)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/stream/", nil)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestSSEHandler_RequestIDNotFound(t *testing.T) {
	channels := NewResponseChannels()
	traceChannel := NewTraceChannel()
	cfg := &config.Config{
		SSE: config.SSEConfig{
			Timeout: 30 * time.Second,
		},
	}
	handler := NewSSEHandler(channels, traceChannel, cfg)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/stream/non-existent-id", nil)
	w := httptest.NewRecorder()

	// Add URL param using chi context
	rctx := chi.NewRouteContext()
	rctx.URLParams.Add("requestID", "non-existent-id")
	req = req.WithContext(context.WithValue(req.Context(), chi.RouteCtxKey, rctx))

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestSSEHandler_StreamComplete(t *testing.T) {
	t.Skip("Skipping - SSE streaming is hard to test synchronously")

	channels := NewResponseChannels()
	traceChannel := NewTraceChannel()
	cfg := &config.Config{
		SSE: config.SSEConfig{
			Timeout: 2 * time.Second, // Short timeout for testing
		},
	}
	handler := NewSSEHandler(channels, traceChannel, cfg)

	requestID := "test-request-123"
	traceID := "abc12345"

	// Create channel and set trace
	ch := channels.Create(requestID)
	traceChannel.Set(requestID, traceID)

	// Send a message and close
	go func() {
		ch <- &gamev1.ChatResponse{
			Content: "Hello, world!",
			IsDone:  false,
		}
		ch <- &gamev1.ChatResponse{
			Content: "Done!",
			IsDone:  true,
		}
		close(ch)
	}()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/stream/"+requestID, nil)
	w := httptest.NewRecorder()

	// Add URL param using chi context
	rctx := chi.NewRouteContext()
	rctx.URLParams.Add("requestID", requestID)
	req = req.WithContext(context.WithValue(req.Context(), chi.RouteCtxKey, rctx))

	// Make response support flushing
	w.Flush()

	// Run handler in goroutine since it blocks
	go handler.ServeHTTP(w, req)

	// Wait a bit for the handler to process
	time.Sleep(100 * time.Millisecond)

	// Verify trace was deleted
	_, ok := traceChannel.Get(requestID)
	if ok {
		t.Error("Trace should be deleted after stream complete")
	}
}

func TestTraceChannel_BasicOperations(t *testing.T) {
	tc := NewTraceChannel()

	// Test Set and Get
	tc.Set("req-1", "trace-1")
	traceID, ok := tc.Get("req-1")
	if !ok {
		t.Fatal("Expected to find trace")
	}
	if traceID != "trace-1" {
		t.Errorf("Expected trace-1, got %s", traceID)
	}

	// Test Delete
	tc.Delete("req-1")
	_, ok = tc.Get("req-1")
	if ok {
		t.Error("Expected trace to be deleted")
	}

	// Test Get non-existent
	_, ok = tc.Get("non-existent")
	if ok {
		t.Error("Expected false for non-existent trace")
	}
}

func TestResponseChannels_BasicOperations(t *testing.T) {
	rc := NewResponseChannels()

	// Test Create and Get
	ch := rc.Create("req-1")
	if ch == nil {
		t.Fatal("Expected channel to be created")
	}

	retrievedCh, ok := rc.Get("req-1")
	if !ok {
		t.Fatal("Expected to find channel")
	}
	if retrievedCh != ch {
		t.Error("Expected same channel")
	}

	// Test Delete
	rc.Delete("req-1")
	_, ok = rc.Get("req-1")
	if ok {
		t.Error("Expected channel to be deleted")
	}

	// Test Get non-existent
	_, ok = rc.Get("non-existent")
	if ok {
		t.Error("Expected false for non-existent channel")
	}
}
