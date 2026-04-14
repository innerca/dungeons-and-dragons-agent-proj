package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	gamev1 "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/gen/game/v1"
)

// MockGRPCClient for testing - properly implements the interface
type MockGRPCClient struct {
	CreatePlayerFunc       func(ctx context.Context, req *gamev1.CreatePlayerRequest, traceID string) (*gamev1.CreatePlayerResponse, error)
	AuthenticatePlayerFunc func(ctx context.Context, req *gamev1.AuthRequest, traceID string) (*gamev1.AuthResponse, error)
	CreateCharacterFunc    func(ctx context.Context, req *gamev1.CreateCharacterRequest, traceID string) (*gamev1.CreateCharacterResponse, error)
	GetPlayerStateFunc     func(ctx context.Context, req *gamev1.GetPlayerStateRequest, traceID string) (*gamev1.PlayerStateResponse, error)
}

func (m *MockGRPCClient) CreatePlayer(ctx context.Context, req *gamev1.CreatePlayerRequest, traceID string) (*gamev1.CreatePlayerResponse, error) {
	if m.CreatePlayerFunc != nil {
		return m.CreatePlayerFunc(ctx, req, traceID)
	}
	return &gamev1.CreatePlayerResponse{}, nil
}

func (m *MockGRPCClient) AuthenticatePlayer(ctx context.Context, req *gamev1.AuthRequest, traceID string) (*gamev1.AuthResponse, error) {
	if m.AuthenticatePlayerFunc != nil {
		return m.AuthenticatePlayerFunc(ctx, req, traceID)
	}
	return &gamev1.AuthResponse{}, nil
}

func (m *MockGRPCClient) CreateCharacter(ctx context.Context, req *gamev1.CreateCharacterRequest, traceID string) (*gamev1.CreateCharacterResponse, error) {
	if m.CreateCharacterFunc != nil {
		return m.CreateCharacterFunc(ctx, req, traceID)
	}
	return &gamev1.CreateCharacterResponse{}, nil
}

func (m *MockGRPCClient) GetPlayerState(ctx context.Context, req *gamev1.GetPlayerStateRequest, traceID string) (*gamev1.PlayerStateResponse, error) {
	if m.GetPlayerStateFunc != nil {
		return m.GetPlayerStateFunc(ctx, req, traceID)
	}
	return &gamev1.PlayerStateResponse{}, nil
}

// Test register validation - only test what we can without real gRPC
func TestAuthHandler_Register_Validation(t *testing.T) {
	tests := []struct {
		name           string
		body           interface{}
		expectedStatus int
	}{
		{
			name:           "invalid JSON",
			body:           "invalid json",
			expectedStatus: http.StatusBadRequest,
		},
		{
			name: "missing username",
			body: registerRequest{
				Username: "",
				Password: "password123",
			},
			expectedStatus: http.StatusBadRequest,
		},
		{
			name: "missing password",
			body: registerRequest{
				Username: "testuser",
				Password: "",
			},
			expectedStatus: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			handler := &AuthHandler{}
			w := httptest.NewRecorder()

			var req *http.Request
			if bodyStr, ok := tt.body.(string); ok {
				req = httptest.NewRequest(http.MethodPost, "/api/v1/register", bytes.NewReader([]byte(bodyStr)))
			} else {
				bodyBytes, _ := json.Marshal(tt.body)
				req = httptest.NewRequest(http.MethodPost, "/api/v1/register", bytes.NewReader(bodyBytes))
			}

			handler.Register(w, req)

			if w.Code != tt.expectedStatus {
				t.Errorf("Expected status %d, got %d", tt.expectedStatus, w.Code)
			}
		})
	}
}

// Test login validation
func TestAuthHandler_Login_Validation(t *testing.T) {
	tests := []struct {
		name           string
		body           interface{}
		expectedStatus int
	}{
		{
			name:           "invalid JSON",
			body:           "invalid json",
			expectedStatus: http.StatusBadRequest,
		},
		{
			name: "missing credentials",
			body: loginRequest{
				Username: "testuser",
				Password: "",
			},
			expectedStatus: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			handler := &AuthHandler{}
			w := httptest.NewRecorder()

			var req *http.Request
			if bodyStr, ok := tt.body.(string); ok {
				req = httptest.NewRequest(http.MethodPost, "/api/v1/login", bytes.NewReader([]byte(bodyStr)))
			} else {
				bodyBytes, _ := json.Marshal(tt.body)
				req = httptest.NewRequest(http.MethodPost, "/api/v1/login", bytes.NewReader(bodyBytes))
			}

			handler.Login(w, req)

			if w.Code != tt.expectedStatus {
				t.Errorf("Expected status %d, got %d", tt.expectedStatus, w.Code)
			}
		})
	}
}

// Test character creation validation with proper auth context
func TestAuthHandler_CreateCharacter_Validation(t *testing.T) {
	tests := []struct {
		name           string
		playerID       *string
		body           interface{}
		expectedStatus int
	}{
		{
			name:           "missing auth",
			playerID:       nil,
			body:           createCharacterRequest{Name: "Test"},
			expectedStatus: http.StatusUnauthorized,
		},
		{
			name:           "invalid JSON",
			playerID:       strPtr("player-123"),
			body:           "invalid json",
			expectedStatus: http.StatusBadRequest,
		},
		{
			name:     "missing character name",
			playerID: strPtr("player-123"),
			body: createCharacterRequest{
				Name: "",
			},
			expectedStatus: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			handler := &AuthHandler{}
			w := httptest.NewRecorder()

			var req *http.Request
			if bodyStr, ok := tt.body.(string); ok {
				req = httptest.NewRequest(http.MethodPost, "/api/v1/character", bytes.NewReader([]byte(bodyStr)))
			} else {
				bodyBytes, _ := json.Marshal(tt.body)
				req = httptest.NewRequest(http.MethodPost, "/api/v1/character", bytes.NewReader(bodyBytes))
			}

			// Add auth context if provided
			if tt.playerID != nil {
				ctx := context.WithValue(req.Context(), "player_id", *tt.playerID)
				req = req.WithContext(ctx)
			}

			handler.CreateCharacter(w, req)

			if w.Code != tt.expectedStatus {
				t.Errorf("Expected status %d, got %d", tt.expectedStatus, w.Code)
			}
		})
	}
}

// Test get player state validation
func TestAuthHandler_GetPlayerState_Validation(t *testing.T) {
	handler := &AuthHandler{}
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/api/v1/player/state", nil)

	handler.GetPlayerState(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status %d for missing auth, got %d", http.StatusUnauthorized, w.Code)
	}
}

func strPtr(s string) *string {
	return &s
}
