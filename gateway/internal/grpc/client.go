package grpcclient

import (
	"context"
	"log"
	"time"

	gamev1 "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/gen/game/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type Client struct {
	conn   *grpc.ClientConn
	client gamev1.GameServiceClient
}

func New(address string, timeout time.Duration) (*Client, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	conn, err := grpc.DialContext(ctx, address,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		return nil, err
	}

	log.Printf("Connected to GameServer at %s", address)
	return &Client{
		conn:   conn,
		client: gamev1.NewGameServiceClient(conn),
	}, nil
}

func (c *Client) Chat(ctx context.Context, req *gamev1.ChatRequest) (gamev1.GameService_ChatClient, error) {
	return c.client.Chat(ctx, req)
}

func (c *Client) CreatePlayer(ctx context.Context, req *gamev1.CreatePlayerRequest) (*gamev1.CreatePlayerResponse, error) {
	return c.client.CreatePlayer(ctx, req)
}

func (c *Client) AuthenticatePlayer(ctx context.Context, req *gamev1.AuthRequest) (*gamev1.AuthResponse, error) {
	return c.client.AuthenticatePlayer(ctx, req)
}

func (c *Client) CreateCharacter(ctx context.Context, req *gamev1.CreateCharacterRequest) (*gamev1.CreateCharacterResponse, error) {
	return c.client.CreateCharacter(ctx, req)
}

func (c *Client) GetPlayerState(ctx context.Context, req *gamev1.GetPlayerStateRequest) (*gamev1.PlayerStateResponse, error) {
	return c.client.GetPlayerState(ctx, req)
}

func (c *Client) Close() error {
	return c.conn.Close()
}
