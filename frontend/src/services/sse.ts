import type { SSEData } from '../types';

type ChunkHandler = (data: SSEData) => void;
type DoneHandler = () => void;
type ErrorHandler = (error: string) => void;

export function connectSSE(
  url: string,
  onChunk: ChunkHandler,
  onDone: DoneHandler,
  onError: ErrorHandler,
): () => void {
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data: SSEData = JSON.parse(event.data);
      if (data.error) {
        onError(data.error);
        eventSource.close();
        return;
      }
      onChunk(data);
      if (data.is_done) {
        eventSource.close();
        onDone();
      }
    } catch {
      // ignore parse errors
    }
  };

  eventSource.addEventListener('done', () => {
    eventSource.close();
    onDone();
  });

  eventSource.addEventListener('error', () => {
    eventSource.close();
    onError('SSE connection error');
  });

  // Return cleanup function
  return () => {
    eventSource.close();
  };
}
