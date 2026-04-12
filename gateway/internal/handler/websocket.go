package handler

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	gamev1 "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/gen/game/v1"
	grpcclient "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/grpc"
)

// generateTraceID generates a short trace ID (8 hex chars)
func generateTraceID() string {
	b := make([]byte, 4)
	rand.Read(b)
	return hex.EncodeToString(b)
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // CORS handled by middleware
	},
}

type wsMessage struct {
	Message string `json:"message"`
	Model   string `json:"model"`
}

type wsResponse struct {
	RequestID string `json:"request_id"`
	SSEUrl    string `json:"sse_url"`
	TraceID   string `json:"trace_id"`
}

// ResponseChannels stores streaming response channels keyed by request_id
type ResponseChannels struct {
	mu       sync.RWMutex
	channels map[string]chan *gamev1.ChatResponse
}

func NewResponseChannels() *ResponseChannels {
	return &ResponseChannels{
		channels: make(map[string]chan *gamev1.ChatResponse),
	}
}

func (rc *ResponseChannels) Create(requestID string) chan *gamev1.ChatResponse {
	rc.mu.Lock()
	defer rc.mu.Unlock()
	ch := make(chan *gamev1.ChatResponse, 64)
	rc.channels[requestID] = ch
	return ch
}

func (rc *ResponseChannels) Get(requestID string) (chan *gamev1.ChatResponse, bool) {
	rc.mu.RLock()
	defer rc.mu.RUnlock()
	ch, ok := rc.channels[requestID]
	return ch, ok
}

func (rc *ResponseChannels) Delete(requestID string) {
	rc.mu.Lock()
	defer rc.mu.Unlock()
	delete(rc.channels, requestID)
}

type WebSocketHandler struct {
	grpcClient   *grpcclient.Client
	channels     *ResponseChannels
	traceChannel *TraceChannel
	counter      uint64
	mu           sync.Mutex
}

func NewWebSocketHandler(grpcClient *grpcclient.Client, channels *ResponseChannels, traceChannel *TraceChannel) *WebSocketHandler {
	return &WebSocketHandler{
		grpcClient:   grpcClient,
		channels:     channels,
		traceChannel: traceChannel,
	}
}

func (h *WebSocketHandler) nextRequestID() string {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.counter++
	return fmt.Sprintf("req-%d", h.counter)
}

func (h *WebSocketHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}
	defer conn.Close()

	// Extract player_id from auth middleware context
	playerID := ""
	if pid := r.Context().Value("player_id"); pid != nil {
		playerID = pid.(string)
	}

	log.Printf("WebSocket client connected: %s (player=%s)", r.RemoteAddr, playerID)

	for {
		_, msgBytes, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
				log.Printf("WebSocket read error: %v", err)
			}
			break
		}

		var msg wsMessage
		if err := json.Unmarshal(msgBytes, &msg); err != nil {
			log.Printf("Invalid WebSocket message: %v", err)
			continue
		}

		// Input validation
		if msg.Message == "" {
			continue
		}
		if len(msg.Message) > 10000 {
			log.Printf("Message too long from %s: %d chars", r.RemoteAddr, len(msg.Message))
			continue
		}

		requestID := h.nextRequestID()
		traceID := generateTraceID()
		ch := h.channels.Create(requestID)

		// Store trace_id for SSE handler to retrieve
		h.traceChannel.Set(requestID, traceID)

		// Log WebSocket message received
		log.Printf("[INFO] trace=%s step=ws_recv player=%s msg_len=%d", traceID, playerID, len(msg.Message))

		// Start gRPC streaming call in background with player_id and trace_id injected
		go h.streamFromGameServer(requestID, traceID, ch, playerID, &msg)

		// Tell client where to listen for SSE, including trace_id
		resp := wsResponse{
			RequestID: requestID,
			SSEUrl:    fmt.Sprintf("/api/v1/stream/%s", requestID),
			TraceID:   traceID,
		}
		respBytes, _ := json.Marshal(resp)
		if err := conn.WriteMessage(websocket.TextMessage, respBytes); err != nil {
			log.Printf("[ERROR] trace=%s step=ws_write error=\"%s\"", traceID, err.Error())
			break
		}
	}
}

func (h *WebSocketHandler) streamFromGameServer(requestID string, traceID string, ch chan *gamev1.ChatResponse, playerID string, msg *wsMessage) {
	defer close(ch)
	defer h.channels.Delete(requestID)

	// Gateway injects player_id — frontend cannot forge it
	req := &gamev1.ChatRequest{
		PlayerId: playerID,
		Message:  msg.Message,
		Model:    msg.Model,
	}

	startTime := time.Now()
	stream, err := h.grpcClient.Chat(context.Background(), req, traceID)
	if err != nil {
		log.Printf("[ERROR] trace=%s step=grpc_call status=error error=\"%s\"", traceID, err.Error())
		ch <- &gamev1.ChatResponse{Content: "", IsDone: true, Error: err.Error()}
		return
	}

	for {
		resp, err := stream.Recv()
		if err != nil {
			if err.Error() != "EOF" {
				log.Printf("[ERROR] trace=%s step=grpc_stream status=error error=\"%s\"", traceID, err.Error())
			}
			break
		}
		ch <- resp
		if resp.IsDone {
			break
		}
	}

	latencyMs := time.Since(startTime).Milliseconds()
	log.Printf("[INFO] trace=%s step=grpc_complete latency_ms=%d", traceID, latencyMs)
}
