import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useSSE } from '../hooks/useSSE';
import { ChatInput } from '../components/ChatInput';
import { StreamingOutput } from '../components/StreamingOutput';
import type { WSResponse } from '../types';

interface ChatMessage {
  id: string;
  text: string;
  isUser: boolean;
  isStreaming: boolean;
  error: string;
}

const GATEWAY_HOST = import.meta.env.VITE_GATEWAY_HOST || `${window.location.hostname}:8080`;
const WS_URL = `ws://${GATEWAY_HOST}/ws`;
const API_BASE = `http://${GATEWAY_HOST}`;

export function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [model, setModel] = useState('deepseek');
  const { status, lastMessage, send } = useWebSocket(WS_URL);
  const { streamingText, isStreaming, error, startStream } = useSSE();
  const chatEndRef = useRef<HTMLDivElement>(null);
  const activeIdRef = useRef<string>('');

  // Handle WS response (receive request_id + sse_url)
  useEffect(() => {
    if (!lastMessage) return;
    try {
      const resp: WSResponse = JSON.parse(lastMessage);
      activeIdRef.current = resp.request_id;
      setMessages((prev) => [
        ...prev,
        { id: resp.request_id, text: '', isUser: false, isStreaming: true, error: '' },
      ]);
      startStream(API_BASE + resp.sse_url);
    } catch {
      // ignore
    }
  }, [lastMessage, startStream]);

  // Update streaming message text
  useEffect(() => {
    if (!activeIdRef.current) return;
    const id = activeIdRef.current;
    setMessages((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, text: streamingText, isStreaming, error } : m,
      ),
    );
  }, [streamingText, isStreaming, error]);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  const handleSend = useCallback(
    (message: string) => {
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        text: message,
        isUser: true,
        isStreaming: false,
        error: '',
      };
      setMessages((prev) => [...prev, userMsg]);
      send(JSON.stringify({ message, session_id: 'default', model }));
    },
    [send, model],
  );

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1>Sword Art Online - DND</h1>
          <span className="subtitle">Weather Query Demo (MVP)</span>
        </div>
        <div className="header-right">
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="deepseek">deepseek-chat</option>
            <option value="openai">openai / gpt-4</option>
            <option value="anthropic">anthropic / claude</option>
          </select>
          <span className={`status ${status}`}>
            {status === 'connected' ? 'Connected' : status === 'connecting' ? 'Connecting...' : 'Disconnected'}
          </span>
        </div>
      </header>

      <div className="chat-area">
        {messages.length === 0 && (
          <div className="empty-state">Ask me about the weather anywhere in the world</div>
        )}
        {messages.map((msg) => (
          <StreamingOutput
            key={msg.id}
            text={msg.text}
            isStreaming={msg.isStreaming}
            error={msg.error}
            isUser={msg.isUser}
          />
        ))}
        <div ref={chatEndRef} />
      </div>

      <ChatInput onSend={handleSend} disabled={status !== 'connected' || isStreaming} />

      <footer className="footer">
        <span>WS: {WS_URL}</span>
        <span>Gateway :8080 | GameServer :50051 (gRPC)</span>
      </footer>
    </div>
  );
}
