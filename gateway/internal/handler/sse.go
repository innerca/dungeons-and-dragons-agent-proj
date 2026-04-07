package handler

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"

	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/config"
)

type SSEHandler struct {
	channels *ResponseChannels
	cfg      *config.Config
}

func NewSSEHandler(channels *ResponseChannels, cfg *config.Config) *SSEHandler {
	return &SSEHandler{channels: channels, cfg: cfg}
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

	log.Printf("SSE client connected for request: %s", requestID)

	ctx := r.Context()
	timeout := time.After(h.cfg.SSE.Timeout)

	for {
		select {
		case <-ctx.Done():
			log.Printf("SSE client disconnected: %s", requestID)
			return
		case <-timeout:
			log.Printf("SSE timeout for request: %s", requestID)
			fmt.Fprintf(w, "event: error\ndata: {\"error\":\"timeout\"}\n\n")
			flusher.Flush()
			return
		case resp, ok := <-ch:
			if !ok {
				// Channel closed, stream complete
				fmt.Fprintf(w, "event: done\ndata: {}\n\n")
				flusher.Flush()
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
