package handler

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

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
	traceID := generateTraceID()
	startTime := time.Now()

	var req registerRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("[ERROR] trace=%s step=auth_register status=error error=\"invalid_request_body\" path=%s", traceID, r.URL.Path)
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	if req.Username == "" || req.Password == "" {
		log.Printf("[ERROR] trace=%s step=auth_register status=error error=\"missing_credentials\"", traceID)
		http.Error(w, `{"error":"username and password are required"}`, http.StatusBadRequest)
		return
	}
	if req.DisplayName == "" {
		req.DisplayName = req.Username
	}

	log.Printf("[INFO] trace=%s step=auth_register user=%s", traceID, req.Username)

	resp, err := h.grpcClient.CreatePlayer(r.Context(), &gamev1.CreatePlayerRequest{
		Username:    req.Username,
		DisplayName: req.DisplayName,
		Password:    req.Password,
	}, traceID)
	if err != nil {
		log.Printf("[ERROR] trace=%s step=grpc_create_player status=error error=\"%s\"", traceID, err.Error())
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	if resp.Error != "" {
		log.Printf("[ERROR] trace=%s step=auth_register status=error error=\"%s\"", traceID, resp.Error)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(authResponse{Error: resp.Error})
		return
	}

	latencyMs := time.Since(startTime).Milliseconds()
	log.Printf("[INFO] trace=%s step=auth_register_complete player_id=%s latency_ms=%d", traceID, resp.PlayerId, latencyMs)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(authResponse{
		PlayerID: resp.PlayerId,
		Token:    resp.Token,
	})
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	traceID := generateTraceID()
	startTime := time.Now()

	var req loginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("[ERROR] trace=%s step=auth_login status=error error=\"invalid_request_body\" path=%s", traceID, r.URL.Path)
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	if req.Username == "" || req.Password == "" {
		log.Printf("[ERROR] trace=%s step=auth_login status=error error=\"missing_credentials\"", traceID)
		http.Error(w, `{"error":"username and password are required"}`, http.StatusBadRequest)
		return
	}

	log.Printf("[INFO] trace=%s step=auth_login user=%s", traceID, req.Username)

	resp, err := h.grpcClient.AuthenticatePlayer(r.Context(), &gamev1.AuthRequest{
		Username: req.Username,
		Password: req.Password,
	}, traceID)
	if err != nil {
		log.Printf("[ERROR] trace=%s step=grpc_auth_player status=error error=\"%s\"", traceID, err.Error())
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	if resp.Error != "" {
		log.Printf("[ERROR] trace=%s step=auth_login status=error error=\"%s\"", traceID, resp.Error)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(authResponse{Error: resp.Error})
		return
	}

	latencyMs := time.Since(startTime).Milliseconds()
	log.Printf("[INFO] trace=%s step=auth_login_complete player_id=%s latency_ms=%d", traceID, resp.PlayerId, latencyMs)

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
	traceID := generateTraceID()
	startTime := time.Now()

	playerID, ok := r.Context().Value("player_id").(string)
	if !ok || playerID == "" {
		log.Printf("[ERROR] trace=%s step=create_character status=error error=\"unauthorized\"", traceID)
		http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
		return
	}

	var req createCharacterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("[ERROR] trace=%s step=create_character status=error error=\"invalid_request_body\" path=%s", traceID, r.URL.Path)
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	if req.Name == "" {
		log.Printf("[ERROR] trace=%s step=create_character status=error error=\"missing_name\"", traceID)
		http.Error(w, `{"error":"character name is required"}`, http.StatusBadRequest)
		return
	}

	log.Printf("[INFO] trace=%s step=create_character player_id=%s name=%s", traceID, playerID, req.Name)

	resp, err := h.grpcClient.CreateCharacter(r.Context(), &gamev1.CreateCharacterRequest{
		PlayerId: playerID,
		Name:     req.Name,
		StatStr:  req.StatSTR,
		StatAgi:  req.StatAGI,
		StatVit:  req.StatVIT,
		StatInt:  req.StatINT,
		StatDex:  req.StatDEX,
		StatLuk:  req.StatLUK,
	}, traceID)
	if err != nil {
		log.Printf("[ERROR] trace=%s step=grpc_create_character status=error error=\"%s\"", traceID, err.Error())
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	if resp.Error != "" {
		log.Printf("[ERROR] trace=%s step=create_character status=error error=\"%s\"", traceID, resp.Error)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(createCharacterResponse{Error: resp.Error})
		return
	}

	latencyMs := time.Since(startTime).Milliseconds()
	log.Printf("[INFO] trace=%s step=create_character_complete character_id=%s latency_ms=%d", traceID, resp.CharacterId, latencyMs)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(createCharacterResponse{CharacterID: resp.CharacterId})
}

func (h *AuthHandler) GetPlayerState(w http.ResponseWriter, r *http.Request) {
	traceID := generateTraceID()
	startTime := time.Now()

	playerID, ok := r.Context().Value("player_id").(string)
	if !ok || playerID == "" {
		log.Printf("[ERROR] trace=%s step=get_player_state status=error error=\"unauthorized\"", traceID)
		http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
		return
	}

	log.Printf("[INFO] trace=%s step=get_player_state player_id=%s", traceID, playerID)

	resp, err := h.grpcClient.GetPlayerState(r.Context(), &gamev1.GetPlayerStateRequest{
		PlayerId: playerID,
	}, traceID)
	if err != nil {
		log.Printf("[ERROR] trace=%s step=grpc_get_player_state status=error error=\"%s\"", traceID, err.Error())
		http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
		return
	}

	if resp.Error != "" {
		log.Printf("[ERROR] trace=%s step=get_player_state status=error error=\"%s\"", traceID, resp.Error)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": resp.Error})
		return
	}

	latencyMs := time.Since(startTime).Milliseconds()
	log.Printf("[INFO] trace=%s step=get_player_state_complete player_id=%s latency_ms=%d", traceID, playerID, latencyMs)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
