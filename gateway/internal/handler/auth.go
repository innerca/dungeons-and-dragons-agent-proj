package handler

import (
	"encoding/json"
	"log"
	"net/http"

	gamev1 "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/gen/game/v1"
	grpcclient "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/internal/grpc"
)

type AuthHandler struct {
	grpcClient *grpcclient.Client
}

func NewAuthHandler(grpcClient *grpcclient.Client) *AuthHandler {
	return &AuthHandler{grpcClient: grpcClient}
}

type registerRequest struct {
	Username    string `json:"username"`
	DisplayName string `json:"display_name"`
	Password    string `json:"password"`
}

type loginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type authResponse struct {
	PlayerID string `json:"player_id,omitempty"`
	Token    string `json:"token,omitempty"`
	Error    string `json:"error,omitempty"`
}

func (h *AuthHandler) Register(w http.ResponseWriter, r *http.Request) {
	var req registerRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	if req.Username == "" || req.Password == "" {
		http.Error(w, `{"error":"username and password are required"}`, http.StatusBadRequest)
		return
	}
	if req.DisplayName == "" {
		req.DisplayName = req.Username
	}

	resp, err := h.grpcClient.CreatePlayer(r.Context(), &gamev1.CreatePlayerRequest{
		Username:    req.Username,
		DisplayName: req.DisplayName,
		Password:    req.Password,
	})
	if err != nil {
		log.Printf("Register gRPC error: %v", err)
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	if resp.Error != "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(authResponse{Error: resp.Error})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(authResponse{
		PlayerID: resp.PlayerId,
		Token:    resp.Token,
	})
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	var req loginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	if req.Username == "" || req.Password == "" {
		http.Error(w, `{"error":"username and password are required"}`, http.StatusBadRequest)
		return
	}

	resp, err := h.grpcClient.AuthenticatePlayer(r.Context(), &gamev1.AuthRequest{
		Username: req.Username,
		Password: req.Password,
	})
	if err != nil {
		log.Printf("Login gRPC error: %v", err)
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	if resp.Error != "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(authResponse{Error: resp.Error})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(authResponse{
		PlayerID: resp.PlayerId,
		Token:    resp.Token,
	})
}

type createCharacterRequest struct {
	Name    string `json:"name"`
	StatSTR int32  `json:"stat_str"`
	StatAGI int32  `json:"stat_agi"`
	StatVIT int32  `json:"stat_vit"`
	StatINT int32  `json:"stat_int"`
	StatDEX int32  `json:"stat_dex"`
	StatLUK int32  `json:"stat_luk"`
}

type createCharacterResponse struct {
	CharacterID string `json:"character_id,omitempty"`
	Error       string `json:"error,omitempty"`
}

func (h *AuthHandler) CreateCharacter(w http.ResponseWriter, r *http.Request) {
	playerID := r.Context().Value("player_id")
	if playerID == nil {
		http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
		return
	}

	var req createCharacterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	if req.Name == "" {
		http.Error(w, `{"error":"character name is required"}`, http.StatusBadRequest)
		return
	}

	resp, err := h.grpcClient.CreateCharacter(r.Context(), &gamev1.CreateCharacterRequest{
		PlayerId: playerID.(string),
		Name:     req.Name,
		StatStr:  req.StatSTR,
		StatAgi:  req.StatAGI,
		StatVit:  req.StatVIT,
		StatInt:  req.StatINT,
		StatDex:  req.StatDEX,
		StatLuk:  req.StatLUK,
	})
	if err != nil {
		log.Printf("CreateCharacter gRPC error: %v", err)
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	if resp.Error != "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(createCharacterResponse{Error: resp.Error})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(createCharacterResponse{CharacterID: resp.CharacterId})
}

func (h *AuthHandler) GetPlayerState(w http.ResponseWriter, r *http.Request) {
	playerID := r.Context().Value("player_id")
	if playerID == nil {
		http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
		return
	}

	resp, err := h.grpcClient.GetPlayerState(r.Context(), &gamev1.GetPlayerStateRequest{
		PlayerId: playerID.(string),
	})
	if err != nil {
		log.Printf("GetPlayerState gRPC error: %v", err)
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	if resp.Error != "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": resp.Error})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
