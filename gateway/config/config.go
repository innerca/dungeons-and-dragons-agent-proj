package config

import (
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

type ServerConfig struct {
	Port         int           `yaml:"port"`
	ReadTimeout  time.Duration `yaml:"read_timeout"`
	WriteTimeout time.Duration `yaml:"write_timeout"`
}

type GameServerConfig struct {
	Address string        `yaml:"address"`
	Timeout time.Duration `yaml:"timeout"`
}

type SSEConfig struct {
	Timeout time.Duration `yaml:"timeout"`
}

type RedisAuthConfig struct {
	AuthKeyPrefix string `yaml:"auth_key_prefix"`
}

type CORSConfig struct {
	AllowedOrigins []string `yaml:"allowed_origins"`
	AllowedMethods []string `yaml:"allowed_methods"`
}

type LoggingConfig struct {
	Level string `yaml:"level"`
}

type Config struct {
	Server     ServerConfig     `yaml:"server"`
	GameServer GameServerConfig `yaml:"gameserver"`
	SSE        SSEConfig        `yaml:"sse"`
	Redis      RedisAuthConfig  `yaml:"redis"`
	CORS       CORSConfig       `yaml:"cors"`
	Logging    LoggingConfig    `yaml:"logging"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	cfg := &Config{
		Server: ServerConfig{
			Port:         8080,
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 120 * time.Second,
		},
		GameServer: GameServerConfig{
			Address: "localhost:50051",
			Timeout: 60 * time.Second,
		},
		SSE: SSEConfig{
			Timeout: 120 * time.Second,
		},
		Redis: RedisAuthConfig{
			AuthKeyPrefix: "sao:auth:token:",
		},
	}

	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, err
	}

	return cfg, nil
}
