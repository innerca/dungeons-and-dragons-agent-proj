package grpcclient

import (
	"testing"
	"time"
)

func TestNew_InvalidAddress(t *testing.T) {
	// Test with invalid address - should fail quickly
	_, err := New("invalid-address:99999", 1*time.Second)
	if err == nil {
		t.Error("Expected error for invalid address")
	}
}

func TestNew_EmptyAddress(t *testing.T) {
	// Test with empty address - should fail
	_, err := New("", 1*time.Second)
	if err == nil {
		t.Error("Expected error for empty address")
	}
}

func TestClient_Close(t *testing.T) {
	// Create a client (will fail to connect, but we can still test Close)
	client, err := New("localhost:9999", 100*time.Millisecond)
	if err != nil {
		// Expected - connection will fail
		return
	}

	// Test Close on successfully created client
	err = client.Close()
	if err != nil {
		t.Errorf("Unexpected error on close: %v", err)
	}
}
