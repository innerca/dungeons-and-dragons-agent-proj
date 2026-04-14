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

// MockGRPCClient for testing
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

func TestAuthHandler_Register_MissingFields(t *testing.T) {
	handler := &AuthHandler{}

	reqBody := registerRequest{
		Username: "testuser",
		Password: "",
	}
	body, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/register", bytes.NewReader(body))
	w := httptest.NewRecorder()

	handler.Register(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestAuthHandler_Register_InvalidBody(t *testing.T) {
	handler := &AuthHandler{}

	req := httptest.NewRequest(http.MethodPost, "/api/v1/register", bytes.NewReader([]byte("invalid json")))
	w := httptest.NewRecorder()

	handler.Register(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestAuthHandler_Login_MissingFields(t *testing.T) {
	handler := &AuthHandler{}

	reqBody := loginRequest{
		Username: "testuser",
		Password: "",
	}
	body, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/login", bytes.NewReader(body))
	w := httptest.NewRecorder()

	handler.Login(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestAuthHandler_Login_InvalidBody(t *testing.T) {
	handler := &AuthHandler{}

	req := httptest.NewRequest(http.MethodPost, "/api/v1/login", bytes.NewReader([]byte("invalid json")))
	w := httptest.NewRecorder()

	handler.Login(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestAuthHandler_CreateCharacter_MissingAuth(t *testing.T) {
	handler := &AuthHandler{}

	reqBody := createCharacterRequest{
		Name: "Test Character",
	}
	body, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/character", bytes.NewReader(body))
	w := httptest.NewRecorder()

	handler.CreateCharacter(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status %d, got %d", http.StatusUnauthorized, w.Code)
	}
}

func TestAuthHandler_CreateCharacter_InvalidBody(t *testing.T) {
	handler := &AuthHandler{}

	req := httptest.NewRequest(http.MethodPost, "/api/v1/character", bytes.NewReader([]byte("invalid json")))
	ctx := context.WithValue(req.Context(), "player_id", "player-123")
	req = req.WithContext(ctx)
	w := httptest.NewRecorder()

	handler.CreateCharacter(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestAuthHandler_CreateCharacter_MissingName(t *testing.T) {
	handler := &AuthHandler{}

	reqBody := createCharacterRequest{
		Name: "",
	}
	body, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/character", bytes.NewReader(body))
	ctx := context.WithValue(req.Context(), "player_id", "player-123")
	req = req.WithContext(ctx)
	w := httptest.NewRecorder()

	handler.CreateCharacter(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status %d, got %d", http.StatusBadRequest, w.Code)
	}
}

func TestAuthHandler_GetPlayerState_MissingAuth(t *testing.T) {
	handler := &AuthHandler{}

	req := httptest.NewRequest(http.MethodGet, "/api/v1/player/state", nil)
	w := httptest.NewRecorder()

	handler.GetPlayerState(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status %d, got %d", http.StatusUnauthorized, w.Code)
	}
}
