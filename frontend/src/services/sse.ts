import type { SSEData } from '../types';

type ChunkHandler = (data: SSEData) => void;
type DoneHandler = () => void;
type ErrorHandler = (error: string) => void;

export function connectSSE(
  url: string,
  onChunk: ChunkHandler,
  onDone: DoneHandler,
  onError: ErrorHandler,
  token?: string,
): () => void {
  const controller = new AbortController();

  // Use fetch with ReadableStream to support auth headers
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  fetch(url, { headers, signal: controller.signal })
    .then(async (response) => {
      if (!response.ok) {
        onError(`HTTP ${response.status}`);
        return;
      }
      const reader = response.body?.getReader();
      if (!reader) { onError('No response body'); return; }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) { onDone(); break; }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data: SSEData = JSON.parse(line.slice(6));
            if (data.error) { onError(data.error); return; }
            onChunk(data);
            if (data.is_done) { onDone(); return; }
          } catch { /* ignore parse errors */ }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError('SSE connection error');
      }
    });

  return () => { controller.abort(); };
}
