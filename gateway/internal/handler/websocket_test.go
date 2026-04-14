package handler

import (
	"testing"
)

func TestGenerateTraceID(t *testing.T) {
	// Generate multiple trace IDs to ensure uniqueness and format
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

		// Check uniqueness (should be unique with high probability)
		if seen[traceID] {
			t.Logf("Warning: Duplicate traceID generated: %s", traceID)
		}
		seen[traceID] = true
	}
}

func TestResponseChannels_Create(t *testing.T) {
	rc := NewResponseChannels()

	ch := rc.Create("req-1")
	if ch == nil {
		t.Fatal("Expected channel to be created")
	}

	// Verify channel is retrievable
	retrieved, ok := rc.Get("req-1")
	if !ok {
		t.Fatal("Expected to retrieve channel")
	}
	if retrieved != ch {
		t.Error("Expected same channel instance")
	}
}

func TestResponseChannels_GetNonExistent(t *testing.T) {
	rc := NewResponseChannels()

	_, ok := rc.Get("non-existent")
	if ok {
		t.Error("Expected false for non-existent channel")
	}
}

func TestResponseChannels_DeleteWS(t *testing.T) {
	rc := NewResponseChannels()

	rc.Create("req-1")
	rc.Delete("req-1")

	_, ok := rc.Get("req-1")
	if ok {
		t.Error("Expected channel to be deleted")
	}
}

func TestResponseChannels_MultipleChannels(t *testing.T) {
	rc := NewResponseChannels()

	ch1 := rc.Create("req-1")
	ch2 := rc.Create("req-2")
	ch3 := rc.Create("req-3")

	// All should be different
	if ch1 == ch2 || ch2 == ch3 || ch1 == ch3 {
		t.Error("Expected different channel instances")
	}

	// All should be retrievable
	if _, ok := rc.Get("req-1"); !ok {
		t.Error("Failed to get req-1")
	}
	if _, ok := rc.Get("req-2"); !ok {
		t.Error("Failed to get req-2")
	}
	if _, ok := rc.Get("req-3"); !ok {
		t.Error("Failed to get req-3")
	}
}

func TestTraceChannel_SetGet(t *testing.T) {
	tc := NewTraceChannel()

	tc.Set("req-1", "trace-abc")
	traceID, ok := tc.Get("req-1")
	if !ok {
		t.Fatal("Expected to find trace")
	}
	if traceID != "trace-abc" {
		t.Errorf("Expected trace-abc, got %s", traceID)
	}
}

func TestTraceChannel_GetNonExistent(t *testing.T) {
	tc := NewTraceChannel()

	_, ok := tc.Get("non-existent")
	if ok {
		t.Error("Expected false for non-existent trace")
	}
}

func TestTraceChannel_DeleteWS(t *testing.T) {
	tc := NewTraceChannel()

	tc.Set("req-1", "trace-abc")
	tc.Delete("req-1")

	_, ok := tc.Get("req-1")
	if ok {
		t.Error("Expected trace to be deleted")
	}
}

func TestTraceChannel_Overwrite(t *testing.T) {
	tc := NewTraceChannel()

	tc.Set("req-1", "trace-1")
	tc.Set("req-1", "trace-2")

	traceID, ok := tc.Get("req-1")
	if !ok {
		t.Fatal("Expected to find trace")
	}
	if traceID != "trace-2" {
		t.Errorf("Expected trace-2, got %s", traceID)
	}
}

func TestWebSocketHandler_NextRequestID(t *testing.T) {
	handler := NewWebSocketHandler(nil, NewResponseChannels(), NewTraceChannel())

	id1 := handler.nextRequestID()
	id2 := handler.nextRequestID()
	id3 := handler.nextRequestID()

	if id1 == id2 || id2 == id3 || id1 == id3 {
		t.Error("Expected unique request IDs")
	}

	// Check format
	if id1 != "req-1" || id2 != "req-2" || id3 != "req-3" {
		t.Errorf("Expected req-1, req-2, req-3, got %s, %s, %s", id1, id2, id3)
	}
}
