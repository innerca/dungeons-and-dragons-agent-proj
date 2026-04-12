package handler

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/go-chi/chi/v5"

	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/config"
)

// TraceChannel stores trace_id for a request
type TraceChannel struct {
	mu       sync.RWMutex
	traceIDs map[string]string
}

func NewTraceChannel() *TraceChannel {
	return &TraceChannel{
		traceIDs: make(map[string]string),
	}
}

func (tc *TraceChannel) Set(requestID string, traceID string) {
	tc.mu.Lock()
	defer tc.mu.Unlock()
	tc.traceIDs[requestID] = traceID
}

func (tc *TraceChannel) Get(requestID string) (string, bool) {
	tc.mu.RLock()
	defer tc.mu.RUnlock()
	traceID, ok := tc.traceIDs[requestID]
	return traceID, ok
}

func (tc *TraceChannel) Delete(requestID string) {
	tc.mu.Lock()
	defer tc.mu.Unlock()
	delete(tc.traceIDs, requestID)
}

type SSEHandler struct {
	channels     *ResponseChannels
	traceChannel *TraceChannel
	cfg          *config.Config
}

func NewSSEHandler(channels *ResponseChannels, traceChannel *TraceChannel, cfg *config.Config) *SSEHandler {
	return &SSEHandler{channels: channels, traceChannel: traceChannel, cfg: cfg}
}

func (h *SSEHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	requestID := chi.URLParam(r, "requestID")
	if requestID == "" {
		http.Error(w, "missing request_id", http.StatusBadRequest)
		return
	}

	ch, ok := h.channels.Get(requestID)
	if !ok {
		http.Error(w, "request_id not found", http.StatusNotFound)
		return
	}

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming not supported", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no")
	flusher.Flush()

	// Get trace_id for this request
	traceID, _ := h.traceChannel.Get(requestID)
	if traceID == "" {
		traceID = "unknown"
	}

	// Send trace_id as first event
	fmt.Fprintf(w, "event: trace\ndata: {\"trace_id\":\"%s\"}\n\n", traceID)
	flusher.Flush()

	log.Printf("[INFO] trace=%s step=sse_connect request_id=%s", traceID, requestID)

	ctx := r.Context()
	timeout := time.After(h.cfg.SSE.Timeout)

	for {
		select {
		case <-ctx.Done():
			log.Printf("[INFO] trace=%s step=sse_disconnect request_id=%s", traceID, requestID)
			h.traceChannel.Delete(requestID)
			return
		case <-timeout:
			log.Printf("[ERROR] trace=%s step=sse_timeout request_id=%s", traceID, requestID)
			fmt.Fprintf(w, "event: error\ndata: {\"error\":\"timeout\"}\n\n")
			flusher.Flush()
			h.traceChannel.Delete(requestID)
			return
		case resp, ok := <-ch:
			if !ok {
				// Channel closed, stream complete
				fmt.Fprintf(w, "event: done\ndata: {}\n\n")
				flusher.Flush()
				h.traceChannel.Delete(requestID)
				return
			}

			data, _ := json.Marshal(map[string]interface{}{
				"content": resp.Content,
				"is_done": resp.IsDone,
				"error":   resp.Error,
			})

			fmt.Fprintf(w, "data: %s\n\n", data)
			flusher.Flush()

			if resp.IsDone {
				return
			}
		}
	}
}
