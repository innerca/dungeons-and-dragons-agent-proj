import type { AuthResponse, PlayerState } from '../types';

const GATEWAY_HOST = import.meta.env.VITE_GATEWAY_HOST || '';
export const API_BASE = GATEWAY_HOST ? `http://${GATEWAY_HOST}` : '';

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await resp.json();

  if (!resp.ok && !data.error) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return data as T;
}

export async function register(username: string, displayName: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, display_name: displayName, password }),
  });
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function createCharacter(
  name: string, stats: { str: number; agi: number; vit: number; int: number; dex: number; luk: number }
): Promise<{ character_id?: string; error?: string }> {
  return apiFetch('/api/v1/character', {
    method: 'POST',
    body: JSON.stringify({
      name,
      stat_str: stats.str,
      stat_agi: stats.agi,
      stat_vit: stats.vit,
      stat_int: stats.int,
      stat_dex: stats.dex,
      stat_luk: stats.luk,
    }),
  });
}

export async function getPlayerState(): Promise<PlayerState> {
  return apiFetch<PlayerState>('/api/v1/player/state');
}
