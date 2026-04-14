package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/redis/go-redis/v9"

	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/config"
	grpcclient "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/grpc"
	"github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/server"
)

func main() {
	configPath := os.Getenv("GATEWAY_CONFIG")
	if configPath == "" {
		configPath = "config/config.yaml"
	}

	cfg, err := config.Load(configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	log.Printf("Connecting to GameServer at %s...", cfg.GameServer.Address)
	grpcClient, err := grpcclient.New(cfg.GameServer.Address, cfg.GameServer.Timeout)
	if err != nil {
		log.Fatalf("Failed to connect to GameServer: %v", err)
	}
	defer grpcClient.Close()

	// Connect to Redis for auth token validation
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://localhost:6379/0"
	}
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("Invalid REDIS_URL: %v", err)
	}
	rdb := redis.NewClient(opt)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Printf("WARNING: Redis connection failed (auth will not work): %v", err)
	} else {
		log.Printf("Connected to Redis")
	}
	defer rdb.Close()

	handler := server.NewHTTPServer(cfg, grpcClient, rdb)

	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.Server.Port),
		Handler:      handler,
		ReadTimeout:  cfg.Server.ReadTimeout,
		WriteTimeout: cfg.Server.WriteTimeout,
	}

	// Start server in goroutine
	go func() {
		log.Printf("Gateway starting on :%d", cfg.Server.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			// Note: log.Fatalf would exit without running deferred cleanup (grpcClient.Close, rdb.Close)
			// This is acceptable here because:
			// 1. Server error is fatal - the gateway cannot function without HTTP server
			// 2. The process is about to exit anyway
			// 3. OS will reclaim resources (socket cleanup)
			log.Fatalf("Server error: %v", err)
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down Gateway...")
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Gateway stopped")
}
