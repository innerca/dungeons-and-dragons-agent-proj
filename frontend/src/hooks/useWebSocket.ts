import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketClient } from '../services/websocket';

type WSStatus = 'connecting' | 'connected' | 'disconnected';

export function useWebSocket(url: string) {
  const [status, setStatus] = useState<WSStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<string>('');
  const clientRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    const client = new WebSocketClient(url, setLastMessage, setStatus);
    clientRef.current = client;
    client.connect();

    return () => {
      client.disconnect();
    };
  }, [url]);

  const send = useCallback((data: string) => {
    clientRef.current?.send(data);
  }, []);

  return { status, lastMessage, send };
}
