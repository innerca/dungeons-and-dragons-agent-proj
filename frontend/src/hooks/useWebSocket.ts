import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketClient } from '../services/websocket';

type WSStatus = 'connecting' | 'connected' | 'disconnected';

export function useWebSocket(url: string, onMessage?: (data: string) => void) {
  const [status, setStatus] = useState<WSStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<string>('');
  const clientRef = useRef<WebSocketClient | null>(null);
  const onMessageRef = useRef(onMessage);
  useEffect(() => {
    onMessageRef.current = onMessage;
  });

  useEffect(() => {
    const client = new WebSocketClient(url, (data) => {
      setLastMessage(data);
      onMessageRef.current?.(data);
    }, setStatus);
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
