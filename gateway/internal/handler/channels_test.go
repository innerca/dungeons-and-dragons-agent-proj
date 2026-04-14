package handler

import (
	"sync"
	"testing"

	gamev1 "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/gen/game/v1"
)

func TestResponseChannels_CreateAndGet(t *testing.T) {
	rc := NewResponseChannels()
	requestID := "test-request-1"

	ch := rc.Create(requestID)
	if ch == nil {
		t.Fatal("Create returned nil channel")
	}

	retrievedCh, ok := rc.Get(requestID)
	if !ok {
		t.Fatal("Get returned false for existing requestID")
	}
	if retrievedCh != ch {
		t.Fatal("Get returned different channel than Create")
	}
}

func TestResponseChannels_Delete(t *testing.T) {
	rc := NewResponseChannels()
	requestID := "test-request-1"

	rc.Create(requestID)

	rc.Delete(requestID)

	_, ok := rc.Get(requestID)
	if ok {
		t.Fatal("Get returned true after Delete")
	}
}

func TestResponseChannels_ConcurrentAccess(t *testing.T) {
	rc := NewResponseChannels()
	numGoroutines := 100
	numOperations := 50

	var wg sync.WaitGroup
	wg.Add(numGoroutines)

	for i := 0; i < numGoroutines; i++ {
		go func(id int) {
			defer wg.Done()
			for j := 0; j < numOperations; j++ {
				requestID := "req-" + string(rune('a'+id)) + "-" + string(rune('0'+j%10))
				ch := rc.Create(requestID)
				_ = ch
				_, _ = rc.Get(requestID)
				rc.Delete(requestID)
			}
		}(i)
	}

	wg.Wait()

	// After all operations, channels should be empty
	rc.mu.RLock()
	if len(rc.channels) != 0 {
		t.Fatalf("Expected 0 channels after concurrent operations, got %d", len(rc.channels))
	}
	rc.mu.RUnlock()
}

func TestTraceChannel_SetAndGet(t *testing.T) {
	tc := NewTraceChannel()
	requestID := "test-request-1"
	traceID := "abc123"

	tc.Set(requestID, traceID)

	retrievedTraceID, ok := tc.Get(requestID)
	if !ok {
		t.Fatal("Get returned false for existing requestID")
	}
	if retrievedTraceID != traceID {
		t.Fatalf("Get returned wrong traceID: got %s, want %s", retrievedTraceID, traceID)
	}
}

func TestTraceChannel_GetMissing(t *testing.T) {
	tc := NewTraceChannel()

	_, ok := tc.Get("non-existent-request")
	if ok {
		t.Fatal("Get returned true for non-existent requestID")
	}
}

func TestGenerateTraceID_Format(t *testing.T) {
	traceID := generateTraceID()

	// Should be 8 hex characters (4 bytes = 8 hex chars)
	if len(traceID) != 8 {
		t.Fatalf("Expected traceID length 8, got %d", len(traceID))
	}

	// Should only contain hex characters
	for _, c := range traceID {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) {
			t.Fatalf("TraceID contains non-hex character: %c", c)
		}
	}
}

func TestResponseChannels_MultipleRequests(t *testing.T) {
	rc := NewResponseChannels()

	// Create multiple channels
	ch1 := rc.Create("req-1")
	ch2 := rc.Create("req-2")
	ch3 := rc.Create("req-3")

	// Verify all can be retrieved
	if _, ok := rc.Get("req-1"); !ok {
		t.Fatal("Failed to get req-1")
	}
	if _, ok := rc.Get("req-2"); !ok {
		t.Fatal("Failed to get req-2")
	}
	if _, ok := rc.Get("req-3"); !ok {
		t.Fatal("Failed to get req-3")
	}

	// Verify channels are different
	if ch1 == ch2 || ch2 == ch3 || ch1 == ch3 {
		t.Fatal("Channels should be different instances")
	}
}

func TestTraceChannel_Delete(t *testing.T) {
	tc := NewTraceChannel()
	requestID := "test-request-1"
	traceID := "abc123"

	tc.Set(requestID, traceID)

	// Verify it exists
	_, ok := tc.Get(requestID)
	if !ok {
		t.Fatal("Get returned false for existing requestID before delete")
	}

	// Delete it
	tc.Delete(requestID)

	// Verify it's gone
	_, ok = tc.Get(requestID)
	if ok {
		t.Fatal("Get returned true after Delete")
	}
}

func TestTraceChannel_ConcurrentAccess(t *testing.T) {
	tc := NewTraceChannel()
	numGoroutines := 50
	numOperations := 30

	var wg sync.WaitGroup
	wg.Add(numGoroutines)

	for i := 0; i < numGoroutines; i++ {
		go func(id int) {
			defer wg.Done()
			for j := 0; j < numOperations; j++ {
				requestID := "req-" + string(rune('a'+id)) + "-" + string(rune('0'+j%10))
				traceID := "trace-" + string(rune('0'+id%10))
				tc.Set(requestID, traceID)
				_, _ = tc.Get(requestID)
				tc.Delete(requestID)
			}
		}(i)
	}

	wg.Wait()

	// After all operations, traceIDs should be empty
	tc.mu.RLock()
	if len(tc.traceIDs) != 0 {
		t.Fatalf("Expected 0 traceIDs after concurrent operations, got %d", len(tc.traceIDs))
	}
	tc.mu.RUnlock()
}

func TestResponseChannels_ChannelBufferSize(t *testing.T) {
	rc := NewResponseChannels()
	requestID := "test-request-1"

	ch := rc.Create(requestID)

	// Channel should have buffer size 64 (as defined in Create method)
	// We can verify this by sending 64 messages without blocking
	for i := 0; i < 64; i++ {
		select {
		case ch <- &gamev1.ChatResponse{Content: "test"}:
			// Success
		default:
			t.Fatal("Channel buffer is smaller than expected")
		}
	}

	// 65th message should block (or we can use non-blocking send)
	select {
	case ch <- &gamev1.ChatResponse{Content: "test"}:
		t.Fatal("Channel buffer is larger than expected (65)")
	default:
		// Expected - buffer is full
	}
}
