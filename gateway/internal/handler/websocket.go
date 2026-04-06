package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"

	"github.com/gorilla/websocket"
	gamev1 "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/gen/game/v1"
	grpcclient "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/grpc"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // CORS handled by middleware
	},
}

type wsMessage struct {
	Message   string `json:"message"`
	SessionID string `json:"session_id"`
	Model     string `json:"model"`
}

type wsResponse struct {
	RequestID string `json:"request_id"`
	SSEUrl    string `json:"sse_url"`
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
	grpcClient *grpcclient.Client
	channels   *ResponseChannels
	counter    uint64
	mu         sync.Mutex
}

func NewWebSocketHandler(grpcClient *grpcclient.Client, channels *ResponseChannels) *WebSocketHandler {
	return &WebSocketHandler{
		grpcClient: grpcClient,
		channels:   channels,
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

	log.Printf("WebSocket client connected: %s", r.RemoteAddr)

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
		ch := h.channels.Create(requestID)

		// Start gRPC streaming call in background
		go h.streamFromGameServer(requestID, ch, &msg)

		// Tell client where to listen for SSE
		resp := wsResponse{
			RequestID: requestID,
			SSEUrl:    fmt.Sprintf("/api/v1/stream/%s", requestID),
		}
		respBytes, _ := json.Marshal(resp)
		if err := conn.WriteMessage(websocket.TextMessage, respBytes); err != nil {
			log.Printf("WebSocket write error: %v", err)
			break
		}
	}
}

func (h *WebSocketHandler) streamFromGameServer(requestID string, ch chan *gamev1.ChatResponse, msg *wsMessage) {
	defer close(ch)
	defer h.channels.Delete(requestID)

	req := &gamev1.ChatRequest{
		SessionId: msg.SessionID,
		Message:   msg.Message,
		Model:     msg.Model,
	}

	stream, err := h.grpcClient.Chat(context.Background(), req)
	if err != nil {
		log.Printf("gRPC Chat error for %s: %v", requestID, err)
		ch <- &gamev1.ChatResponse{Content: "", IsDone: true, Error: err.Error()}
		return
	}

	for {
		resp, err := stream.Recv()
		if err != nil {
			if err.Error() != "EOF" {
				log.Printf("gRPC stream error for %s: %v", requestID, err)
			}
			break
		}
		ch <- resp
		if resp.IsDone {
			break
		}
	}
}
