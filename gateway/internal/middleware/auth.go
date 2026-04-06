package middleware

import (
	"context"
	"net/http"
	"strings"

	"github.com/redis/go-redis/v9"
)

// Auth middleware: validates token from Authorization header or query param,
// resolves player_id from Redis, and injects it into request context.
func Auth(rdb *redis.Client) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			token := extractToken(r)
			if token == "" {
				http.Error(w, `{"error":"missing auth token"}`, http.StatusUnauthorized)
				return
			}

			playerID, err := rdb.Get(r.Context(), "sao:auth:token:"+token).Result()
			if err == redis.Nil || playerID == "" {
				http.Error(w, `{"error":"invalid or expired token"}`, http.StatusUnauthorized)
				return
			}
			if err != nil {
				http.Error(w, `{"error":"auth service unavailable"}`, http.StatusServiceUnavailable)
				return
			}

			ctx := context.WithValue(r.Context(), "player_id", playerID)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func extractToken(r *http.Request) string {
	// Check Authorization header first
	auth := r.Header.Get("Authorization")
	if strings.HasPrefix(auth, "Bearer ") {
		return strings.TrimPrefix(auth, "Bearer ")
	}

	// Fallback to query param (for WebSocket connections)
	return r.URL.Query().Get("token")
}
