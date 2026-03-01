import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useEffect, useRef, useState } from 'react';

export default function Chat() {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { messages, sendMessage, status, stop } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
  });

  const isStreaming = status === 'streaming' || status === 'submitted';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    sendMessage({ text: input });
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  return (
    <div className="chat-root">
      {/* Header */}
      <header className="chat-header">
        <div>
          <div className="chat-header-title">Questline</div>
          <div className="chat-header-sub">Life Trajectory Oracle · Jordan Lee</div>
        </div>
        <div className="chat-header-dot" />
      </header>

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 && !isStreaming ? (
          <div className="chat-empty">
            <div className="chat-empty-glyph">◈</div>
            <div className="chat-empty-text">Begin your inquiry</div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`msg msg--${message.role}`}
            >
              <div className="msg-meta">
                <span className={`msg-role msg-role--${message.role}`}>
                  {message.role === 'user' ? 'You' : 'Oracle'}
                </span>
                <span className="msg-line" />
              </div>
              <div className="msg-body">
                {message.parts.map((part, i) =>
                  part.type === 'text' ? <span key={i}>{part.text}</span> : null
                )}
              </div>
            </div>
          ))
        )}

        {isStreaming && (
          <div className="thinking">
            <span className="thinking-rune">✦</span>
            <span className="thinking-text">
              {status === 'submitted' ? 'Consulting the data' : 'Composing response'}
            </span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <form className="chat-form" onSubmit={handleSubmit}>
          <div className="chat-input-wrap">
            <label className="chat-input-label" htmlFor="chat-input">
              Your query · shift+enter for newline
            </label>
            <textarea
              id="chat-input"
              ref={textareaRef}
              className="chat-input"
              value={input}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask about patterns, scenarios, or actions…"
              disabled={isStreaming}
              rows={1}
            />
          </div>

          {isStreaming ? (
            <button
              type="button"
              className="chat-btn chat-btn--stop"
              onClick={stop}
            >
              ◼ Stop
            </button>
          ) : (
            <button
              type="submit"
              className="chat-btn chat-btn--send"
              disabled={!input.trim()}
            >
              Send ◆
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
