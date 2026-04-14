package handler

import (
	"testing"
)

// Test generateTraceID functionality
func TestGenerateTraceID(t *testing.T) {
	seen := make(map[string]bool)

	for i := 0; i < 100; i++ {
		traceID := generateTraceID()

		// Check length (8 hex chars)
		if len(traceID) != 8 {
			t.Errorf("Expected traceID length 8, got %d", len(traceID))
		}

		// Check hex format
		for _, c := range traceID {
			if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
				t.Errorf("TraceID contains non-hex character: %c in %s", c, traceID)
			}
		}

		// Track for uniqueness check
		seen[traceID] = true
	}

	// With 100 iterations, we should have generated many unique IDs
	if len(seen) < 50 {
		t.Errorf("Expected at least 50 unique trace IDs, got %d", len(seen))
	}
}

// Test WebSocket handler request ID generation
func TestWebSocketHandler_NextRequestID(t *testing.T) {
	handler := NewWebSocketHandler(nil, NewResponseChannels(), NewTraceChannel())

	id1 := handler.nextRequestID()
	id2 := handler.nextRequestID()
	id3 := handler.nextRequestID()

	// Check uniqueness
	if id1 == id2 || id2 == id3 || id1 == id3 {
		t.Error("Expected unique request IDs")
	}

	// Check format
	if id1 != "req-1" || id2 != "req-2" || id3 != "req-3" {
		t.Errorf("Expected req-1, req-2, req-3, got %s, %s, %s", id1, id2, id3)
	}
}

// Test TraceChannel specific operations (not covered in channels_test.go)
func TestTraceChannel_Overwrite(t *testing.T) {
	tc := NewTraceChannel()

	tc.Set("req-1", "trace-1")
	tc.Set("req-1", "trace-2")

	traceID, ok := tc.Get("req-1")
	if !ok {
		t.Fatal("Expected to find trace")
	}
	if traceID != "trace-2" {
		t.Errorf("Expected trace-2 after overwrite, got %s", traceID)
	}
}
