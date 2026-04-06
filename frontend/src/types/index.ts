export interface WSMessage {
  message: string;
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

export interface AuthResponse {
  player_id: string;
  token: string;
  error?: string;
}

export interface PlayerState {
  character_name: string;
  level: number;
  current_hp: number;
  max_hp: number;
  experience: number;
  exp_to_next: number;
  stat_str: number;
  stat_agi: number;
  stat_vit: number;
  stat_int: number;
  stat_dex: number;
  stat_luk: number;
  col: number;
  current_floor: number;
  current_area: string;
  current_location: string;
  error?: string;
}
