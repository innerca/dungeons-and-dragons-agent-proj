package grpcclient

import (
	"context"
	"log"
	"time"

	gamev1 "github.com/innerca/dungeons-and-dragons-agent-proj/gateway/gen/game/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
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

func (c *Client) Chat(ctx context.Context, req *gamev1.ChatRequest, traceID string) (gamev1.GameService_ChatClient, error) {
	md := metadata.Pairs("x-trace-id", traceID)
	ctx = metadata.NewOutgoingContext(ctx, md)
	return c.client.Chat(ctx, req)
}

func (c *Client) CreatePlayer(ctx context.Context, req *gamev1.CreatePlayerRequest, traceID string) (*gamev1.CreatePlayerResponse, error) {
	md := metadata.Pairs("x-trace-id", traceID)
	ctx = metadata.NewOutgoingContext(ctx, md)
	return c.client.CreatePlayer(ctx, req)
}

func (c *Client) AuthenticatePlayer(ctx context.Context, req *gamev1.AuthRequest, traceID string) (*gamev1.AuthResponse, error) {
	md := metadata.Pairs("x-trace-id", traceID)
	ctx = metadata.NewOutgoingContext(ctx, md)
	return c.client.AuthenticatePlayer(ctx, req)
}

func (c *Client) CreateCharacter(ctx context.Context, req *gamev1.CreateCharacterRequest, traceID string) (*gamev1.CreateCharacterResponse, error) {
	md := metadata.Pairs("x-trace-id", traceID)
	ctx = metadata.NewOutgoingContext(ctx, md)
	return c.client.CreateCharacter(ctx, req)
}

func (c *Client) GetPlayerState(ctx context.Context, req *gamev1.GetPlayerStateRequest, traceID string) (*gamev1.PlayerStateResponse, error) {
	md := metadata.Pairs("x-trace-id", traceID)
	ctx = metadata.NewOutgoingContext(ctx, md)
	return c.client.GetPlayerState(ctx, req)
}

func (c *Client) Close() error {
	return c.conn.Close()
}
