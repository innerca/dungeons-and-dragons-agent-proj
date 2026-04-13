import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useSSE } from '../hooks/useSSE';
import { ChatInput } from '../components/ChatInput';
import { StreamingOutput } from '../components/StreamingOutput';
import type { WSResponse, PlayerState } from '../types';
import { getPlayerState, API_BASE } from '../services/api';

interface ChatMessage {
  id: string;
  text: string;
  isUser: boolean;
  isStreaming: boolean;
  error: string;
}

const GATEWAY_HOST = import.meta.env.VITE_GATEWAY_HOST || '';

interface Props {
  onLogout: () => void;
}

export function Home({ onLogout }: Props) {
  const token = localStorage.getItem('token') || '';
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = GATEWAY_HOST || window.location.host;
  const WS_URL = `${wsProtocol}//${wsHost}/ws?token=${token}`;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [model, setModel] = useState('deepseek');
  const [playerState, setPlayerState] = useState<PlayerState | null>(null);
  const { status, lastMessage, send } = useWebSocket(WS_URL);
  const { streamingText, isStreaming, error, startStream } = useSSE();
  const chatEndRef = useRef<HTMLDivElement>(null);
  const activeIdRef = useRef<string>('');
  const hasTriggeredWelcomeRef = useRef<boolean>(false);

  // Load player state
  useEffect(() => {
    getPlayerState().then(setPlayerState).catch(() => {});
  }, []);

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
      startStream(API_BASE + resp.sse_url, token);
    } catch {
      // ignore
    }
  }, [lastMessage, startStream, token]);

  // Update streaming message text
  useEffect(() => {
    if (!activeIdRef.current) return;
    const id = activeIdRef.current;
    setMessages((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, text: streamingText, isStreaming, error } : m,
      ),
    );
    // Refresh state after response completes
    if (!isStreaming && streamingText) {
      getPlayerState().then(setPlayerState).catch(() => {});
    }
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
      send(JSON.stringify({ message, model }));
    },
    [send, model],
  );

  // Auto-trigger welcome message for new players
  useEffect(() => {
    if (messages.length === 0 && playerState?.character_name && !hasTriggeredWelcomeRef.current) {
      hasTriggeredWelcomeRef.current = true;
      // Delay a bit for page render to complete
      const timer = setTimeout(() => {
        handleSend("开始冒险");
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [messages.length, playerState?.character_name, handleSend]);

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1>SAO Progressive DND</h1>
          {playerState && playerState.character_name && (
            <span className="subtitle">
              {playerState.character_name} Lv.{playerState.level} |
              HP {playerState.current_hp}/{playerState.max_hp} |
              Floor {playerState.current_floor} - {playerState.current_area}
            </span>
          )}
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
          <button className="logout-btn" onClick={onLogout}>Logout</button>
        </div>
      </header>

      <div className="chat-area">
        {messages.length === 0 && (
          <div className="empty-state">
            Welcome to Aincrad. You stand in the Town of Beginnings on Floor 1.
            What would you like to do?
          </div>
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
        <span>
          {playerState ? `Col: ${playerState.col} | ${playerState.current_location}` : ''}
        </span>
        <span>Gateway :8080 | GameServer :50051 (gRPC)</span>
      </footer>
    </div>
  );
}
