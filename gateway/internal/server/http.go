package server

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	chimiddleware "github.com/go-chi/chi/v5/middleware"

	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/config"
	grpcclient "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/grpc"
	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/handler"
	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/middleware"
)

func NewHTTPServer(cfg *config.Config, grpcClient *grpcclient.Client) http.Handler {
	r := chi.NewRouter()

	// Middleware
	r.Use(chimiddleware.Logger)
	r.Use(chimiddleware.Recoverer)
	r.Use(chimiddleware.RealIP)
	r.Use(middleware.CORS(cfg.CORS.AllowedOrigins, cfg.CORS.AllowedMethods))

	// Shared response channels between WS and SSE handlers
	channels := handler.NewResponseChannels()

	// Routes
	wsHandler := handler.NewWebSocketHandler(grpcClient, channels)
	sseHandler := handler.NewSSEHandler(channels)

	r.Get("/ws", wsHandler.ServeHTTP)
	r.Get("/api/v1/stream/{requestID}", sseHandler.ServeHTTP)

	// Health check
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	})

	return r
}
