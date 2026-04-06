import { useState, useCallback, useRef } from 'react';
import { connectSSE } from '../services/sse';
import type { SSEData } from '../types';

export function useSSE() {
  const [streamingText, setStreamingText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState('');
  const cleanupRef = useRef<(() => void) | null>(null);

  const startStream = useCallback((url: string, token?: string) => {
    // Cleanup previous stream if any
    cleanupRef.current?.();

    setStreamingText('');
    setIsStreaming(true);
    setError('');

    const cleanup = connectSSE(
      url,
      (data: SSEData) => {
        if (data.content) {
          setStreamingText((prev) => prev + data.content);
        }
      },
      () => {
        setIsStreaming(false);
      },
      (err: string) => {
        setError(err);
        setIsStreaming(false);
      },
      token,
    );

    cleanupRef.current = cleanup;
  }, []);

  const stopStream = useCallback(() => {
    cleanupRef.current?.();
    cleanupRef.current = null;
    setIsStreaming(false);
  }, []);

  return { streamingText, isStreaming, error, startStream, stopStream };
}
