package server

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	chimiddleware "github.com/go-chi/chi/v5/middleware"
	"github.com/redis/go-redis/v9"

	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/config"
	grpcclient "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/grpc"
	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/handler"
	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/middleware"
)

func NewHTTPServer(cfg *config.Config, grpcClient *grpcclient.Client, rdb *redis.Client) http.Handler {
	r := chi.NewRouter()

	// Middleware
	r.Use(chimiddleware.Logger)
	r.Use(chimiddleware.Recoverer)
	r.Use(chimiddleware.RealIP)
	r.Use(middleware.CORS(cfg.CORS.AllowedOrigins, cfg.CORS.AllowedMethods))

	// Shared response channels between WS and SSE handlers
	channels := handler.NewResponseChannels()
	traceChannel := handler.NewTraceChannel()

	wsHandler := handler.NewWebSocketHandler(grpcClient, channels, traceChannel)
	sseHandler := handler.NewSSEHandler(channels, traceChannel, cfg)
	authHandler := handler.NewAuthHandler(grpcClient)

	// Public routes (no auth required)
	r.Post("/api/v1/auth/register", authHandler.Register)
	r.Post("/api/v1/auth/login", authHandler.Login)

	// Health check
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	})

	// Authenticated routes
	r.Group(func(r chi.Router) {
		r.Use(middleware.Auth(rdb, cfg.Redis.AuthKeyPrefix))

		r.Get("/ws", wsHandler.ServeHTTP)
		r.Get("/api/v1/stream/{requestID}", sseHandler.ServeHTTP)
		r.Post("/api/v1/character", authHandler.CreateCharacter)
		r.Get("/api/v1/player/state", authHandler.GetPlayerState)
	})

	return r
}
