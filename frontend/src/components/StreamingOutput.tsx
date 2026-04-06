interface StreamingOutputProps {
  text: string;
  isStreaming: boolean;
  error: string;
  isUser: boolean;
}

export function StreamingOutput({ text, isStreaming, error, isUser }: StreamingOutputProps) {
  if (error) {
    return (
      <div className={`message ${isUser ? 'user' : 'assistant'}`}>
        <div className="message-label">{isUser ? 'You' : 'Assistant'}</div>
        <div className="message-bubble error">{error}</div>
      </div>
    );
  }

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-label">{isUser ? 'You' : 'GameServer (LLM)'}</div>
      <div className="message-bubble">
        {text}
        {isStreaming && <span className="cursor" />}
      </div>
    </div>
  );
}
