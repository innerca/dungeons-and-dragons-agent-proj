export interface WSMessage {
  message: string;
  session_id: string;
  model: string;
}

export interface WSResponse {
  request_id: string;
  sse_url: string;
}

export interface SSEData {
  content: string;
  is_done: boolean;
  error: string;
}
