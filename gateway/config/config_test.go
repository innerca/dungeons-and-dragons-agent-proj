package config

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
	"time"
)

func TestLoadConfig_Valid(t *testing.T) {
	// Use the actual config.yaml file from the project
	// Get the directory of the current test file and construct path relative to it
	_, currentFile, _, _ := runtime.Caller(0)
	currentDir := filepath.Dir(currentFile)
	configPath := filepath.Join(currentDir, "..", "config", "config.yaml")

	cfg, err := Load(configPath)
	if err != nil {
		t.Fatalf("Failed to load valid config: %v", err)
	}

	// Verify server config
	if cfg.Server.Port != 8080 {
		t.Errorf("Expected server port 8080, got %d", cfg.Server.Port)
	}
	if cfg.Server.ReadTimeout != 30*time.Second {
		t.Errorf("Expected read timeout 30s, got %v", cfg.Server.ReadTimeout)
	}
	if cfg.Server.WriteTimeout != 120*time.Second {
		t.Errorf("Expected write timeout 120s, got %v", cfg.Server.WriteTimeout)
	}

	// Verify gameserver config
	if cfg.GameServer.Address != "localhost:50051" {
		t.Errorf("Expected gameserver address localhost:50051, got %s", cfg.GameServer.Address)
	}
	if cfg.GameServer.Timeout != 60*time.Second {
		t.Errorf("Expected gameserver timeout 60s, got %v", cfg.GameServer.Timeout)
	}

	// Verify SSE config
	if cfg.SSE.Timeout != 120*time.Second {
		t.Errorf("Expected SSE timeout 120s, got %v", cfg.SSE.Timeout)
	}

	// Verify Redis config
	if cfg.Redis.AuthKeyPrefix != "sao:auth:token:" {
		t.Errorf("Expected Redis auth key prefix 'sao:auth:token:', got %s", cfg.Redis.AuthKeyPrefix)
	}

	// Verify CORS config
	if len(cfg.CORS.AllowedOrigins) != 1 || cfg.CORS.AllowedOrigins[0] != "http://localhost:5173" {
		t.Errorf("Expected CORS allowed origins [http://localhost:5173], got %v", cfg.CORS.AllowedOrigins)
	}
	if len(cfg.CORS.AllowedMethods) != 3 {
		t.Errorf("Expected 3 CORS allowed methods, got %d", len(cfg.CORS.AllowedMethods))
	}

	// Verify logging config
	if cfg.Logging.Level != "info" {
		t.Errorf("Expected logging level 'info', got %s", cfg.Logging.Level)
	}
}

func TestLoadConfig_InvalidPath(t *testing.T) {
	_, err := Load("/nonexistent/path/config.yaml")
	if err == nil {
		t.Fatal("Expected error for invalid path, got nil")
	}
}

func TestLoadConfig_DefaultValues(t *testing.T) {
	// Create a temporary config file with minimal content
	tmpDir := t.TempDir()
	minimalConfigPath := filepath.Join(tmpDir, "minimal_config.yaml")

	minimalConfig := `
server:
  port: 9090
`
	if err := os.WriteFile(minimalConfigPath, []byte(minimalConfig), 0644); err != nil {
		t.Fatalf("Failed to write minimal config: %v", err)
	}

	cfg, err := Load(minimalConfigPath)
	if err != nil {
		t.Fatalf("Failed to load config: %v", err)
	}

	// Verify overridden value
	if cfg.Server.Port != 9090 {
		t.Errorf("Expected server port 9090, got %d", cfg.Server.Port)
	}

	// Verify default values are applied for unspecified fields
	if cfg.Server.ReadTimeout != 30*time.Second {
		t.Errorf("Expected default read timeout 30s, got %v", cfg.Server.ReadTimeout)
	}
	if cfg.Server.WriteTimeout != 120*time.Second {
		t.Errorf("Expected default write timeout 120s, got %v", cfg.Server.WriteTimeout)
	}
	if cfg.GameServer.Address != "localhost:50051" {
		t.Errorf("Expected default gameserver address localhost:50051, got %s", cfg.GameServer.Address)
	}
	if cfg.GameServer.Timeout != 60*time.Second {
		t.Errorf("Expected default gameserver timeout 60s, got %v", cfg.GameServer.Timeout)
	}
	if cfg.SSE.Timeout != 120*time.Second {
		t.Errorf("Expected default SSE timeout 120s, got %v", cfg.SSE.Timeout)
	}
	if cfg.Redis.AuthKeyPrefix != "sao:auth:token:" {
		t.Errorf("Expected default Redis auth key prefix 'sao:auth:token:', got %s", cfg.Redis.AuthKeyPrefix)
	}
}

func TestLoadConfig_InvalidYAML(t *testing.T) {
	tmpDir := t.TempDir()
	invalidConfigPath := filepath.Join(tmpDir, "invalid_config.yaml")

	invalidConfig := `
server:
  port: not_a_number
`
	if err := os.WriteFile(invalidConfigPath, []byte(invalidConfig), 0644); err != nil {
		t.Fatalf("Failed to write invalid config: %v", err)
	}

	_, err := Load(invalidConfigPath)
	if err == nil {
		t.Fatal("Expected error for invalid YAML, got nil")
	}
}

func TestLoadConfig_EmptyFile(t *testing.T) {
	tmpDir := t.TempDir()
	emptyConfigPath := filepath.Join(tmpDir, "empty_config.yaml")

	if err := os.WriteFile(emptyConfigPath, []byte(""), 0644); err != nil {
		t.Fatalf("Failed to write empty config: %v", err)
	}

	cfg, err := Load(emptyConfigPath)
	if err != nil {
		t.Fatalf("Failed to load empty config: %v", err)
	}

	// All values should be defaults
	if cfg.Server.Port != 8080 {
		t.Errorf("Expected default server port 8080, got %d", cfg.Server.Port)
	}
	if cfg.GameServer.Address != "localhost:50051" {
		t.Errorf("Expected default gameserver address localhost:50051, got %s", cfg.GameServer.Address)
	}
}

func TestConfig_StructFields(t *testing.T) {
	// Test that Config struct has all expected fields
	cfg := &Config{}

	// These should compile if the fields exist
	_ = cfg.Server.Port
	_ = cfg.Server.ReadTimeout
	_ = cfg.Server.WriteTimeout
	_ = cfg.GameServer.Address
	_ = cfg.GameServer.Timeout
	_ = cfg.SSE.Timeout
	_ = cfg.Redis.AuthKeyPrefix
	_ = cfg.CORS.AllowedOrigins
	_ = cfg.CORS.AllowedMethods
	_ = cfg.Logging.Level
}
