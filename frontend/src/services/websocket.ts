type MessageHandler = (data: string) => void;
type StatusHandler = (status: 'connecting' | 'connected' | 'disconnected') => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private onMessage: MessageHandler;
  private onStatus: StatusHandler;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(url: string, onMessage: MessageHandler, onStatus: StatusHandler) {
    this.url = url;
    this.onMessage = onMessage;
    this.onStatus = onStatus;
  }

  connect(): void {
    this.onStatus('connecting');
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.onStatus('connected');
    };

    this.ws.onmessage = (event) => {
      this.onMessage(event.data);
    };

    this.ws.onclose = () => {
      this.onStatus('disconnected');
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  send(data: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    }
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  private scheduleReconnect(): void {
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, 3000);
  }
}
