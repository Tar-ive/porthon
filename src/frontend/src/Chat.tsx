import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { MemoizedMarkdown } from './MemoizedMarkdown';
import { useAgentStream } from './hooks/useAgentStream';

interface Scenario {
  id: string;
  title: string;
  horizon: string;
  likelihood: string;
  summary: string;
  tags: string[];
}

interface Action {
  id: string;
  action: string;
  title?: string;
  data_ref: string;
  pattern_id?: string;
  rationale: string;
  compound_summary: string;
}

const INTENT_COLORS: Record<string, string> = {
  factual: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  pattern: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  advice: 'bg-green-500/20 text-green-300 border-green-500/30',
  reflection: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  emotional: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
};

const DEMO_TOKEN = 'Bearer sk_demo_default';
const DEMO_JSON_HEADERS = {
  'Content-Type': 'application/json',
  Authorization: DEMO_TOKEN,
};

export default function Chat({ scenario, actions = [], onRestart }: { scenario: Scenario; actions?: Action[]; onRestart?: () => void }) {
  const [input, setInput] = useState('');
  const [intent, setIntent] = useState<string | null>(null);
  const [completedActions, setCompletedActions] = useState<Set<string>>(() => {
    try {
      const stored = sessionStorage.getItem('completedActions');
      return stored ? new Set(JSON.parse(stored) as string[]) : new Set();
    } catch { return new Set(); }
  });

  const toggleAction = (id: string) => {
    setCompletedActions(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      sessionStorage.setItem('completedActions', JSON.stringify([...next]));
      return next;
    });
  };
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const intentRef = useRef(setIntent);
  intentRef.current = setIntent;

  // Track previous actionsVersion to detect increments
  const prevActionsVersion = useRef(0);
  const [planUpdated, setPlanUpdated] = useState(false);

  // Live data stream
  const { isAnalyzing, analysisMessage, changedDomain, actionsVersion } = useAgentStream();

  // Show "plan updated" banner when actionsVersion increments
  useEffect(() => {
    if (actionsVersion > prevActionsVersion.current) {
      prevActionsVersion.current = actionsVersion;
      if (actionsVersion > 0) {
        setPlanUpdated(true);
      }
    }
  }, [actionsVersion]);

  // Activate workers on mount
  useEffect(() => {
    fetch('/api/agent/activate', {
      method: 'POST',
      headers: DEMO_JSON_HEADERS,
      body: JSON.stringify({
        scenario_id: scenario.id,
        scenario_title: scenario.title,
        scenario_summary: scenario.summary,
        scenario_horizon: scenario.horizon,
        scenario_likelihood: scenario.likelihood,
        scenario_tags: scenario.tags,
      }),
    }).catch(() => {});
  }, [scenario.horizon, scenario.id, scenario.likelihood, scenario.summary, scenario.title]);

  const [transport] = useState(
    () =>
      new DefaultChatTransport({
        api: '/api/chat',
        body: { scenario, actions },
        fetch: async (requestInfo, init) => {
          const mergedHeaders = {
            ...(init?.headers as Record<string, string> | undefined),
            Authorization: DEMO_TOKEN,
          };
          const res = await fetch(requestInfo, { ...init, headers: mergedHeaders });
          const intentHeader = res.headers.get('x-porthon-intent');
          if (intentHeader && intentHeader !== 'casual') {
            intentRef.current(intentHeader);
          } else {
            intentRef.current(null);
          }
          return res;
        },
      }),
  );

  const { messages, sendMessage, status, stop } = useChat({ transport });

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
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  return (
    <div className="chat-root">
      {/* Header */}
      <header className="chat-header">
        <div>
          <div className="chat-header-title">Questline</div>
          <div className="chat-header-sub">
            {scenario.title} · {scenario.horizon} · Theo Nakamura
          </div>
          {/* <div className="chat-header-brief">
            For freelancers who need one operating surface for leads, delivery pressure, and the next revenue-saving move.
          </div> */}
        </div>
        <div className="chat-header-dot" />
      </header>

      {/* Live data banners */}
      {isAnalyzing && (
        <div className="stream-banner stream-banner--analyzing">
          <span className="stream-banner-dot" />
          {analysisMessage ?? 'Analyzing new data...'}
        </div>
      )}
      {!isAnalyzing && planUpdated && (
        <div className="stream-banner stream-banner--analyzing">
          <span className="stream-banner-dot" style={{ background: '#22c55e' }} />
          Your plan was updated — view actions
        </div>
      )}
      {!isAnalyzing && !planUpdated && changedDomain && (
        <div className="stream-banner stream-banner--analyzing">
          <span className="stream-banner-dot" />
          {`New ${changedDomain} data — trajectories stable`}
        </div>
      )}

      {/* Left context strip + Main chat split */}
      <div className="chat-layout">
        {/* Slim context strip */}
        <div style={{ width: '220px', flexShrink: 0, borderRight: '1px solid #1a1a2e', padding: '1.5rem 1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', height: '100%', paddingBottom: '2rem', overflow: 'hidden' }}>
          {/* Scenario context */}
          <div>
            <div style={{ fontSize: '0.65rem', color: '#555', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.4rem' }}>Active Quest</div>
            <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: 600, lineHeight: 1.4 }}>{scenario?.title}</div>
            {scenario?.horizon && (
              <span style={{ fontSize: '0.7rem', background: '#7B61FF22', color: '#7B61FF', borderRadius: '4px', padding: '2px 6px', marginTop: '0.4rem', display: 'inline-block' }}>
                {scenario.horizon === '1yr' ? '1 Year' : scenario.horizon === '5yr' ? '5 Years' : scenario.horizon}
              </span>
            )}
          </div>

          {/* Live status */}
          <div>
            <div style={{ fontSize: '0.65rem', color: '#555', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.4rem' }}>Status</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: isAnalyzing ? '#F59E0B' : '#22c55e' }} />
              <span style={{ fontSize: '0.8rem', color: '#888' }}>{isAnalyzing ? 'Analyzing...' : 'Live'}</span>
            </div>
          </div>

          {/* Action plan */}
          {actions.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, flex: 1 }}>
              <div style={{ fontSize: '0.65rem', color: '#555', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.5rem', flexShrink: 0 }}>
                This Week · {actions.length} actions
              </div>
              <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.3rem', paddingRight: '2px' }}>
                {actions.map((a, i) => {
                  const done = completedActions.has(a.id);
                  return (
                    <button
                      key={a.id}
                      onClick={() => toggleAction(a.id)}
                      style={{
                        display: 'flex', gap: '0.5rem', alignItems: 'flex-start',
                        background: 'none', border: 'none', cursor: 'pointer',
                        padding: '0.25rem 0', textAlign: 'left', width: '100%',
                      }}
                    >
                      {/* Checkbox */}
                      <span style={{
                        flexShrink: 0, marginTop: '2px',
                        width: '13px', height: '13px',
                        border: `1px solid ${done ? '#7B61FF' : '#333'}`,
                        borderRadius: '3px',
                        background: done ? '#7B61FF' : 'transparent',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'background 0.15s ease, border-color 0.15s ease',
                      }}>
                        {done && (
                          <svg width="8" height="6" viewBox="0 0 8 6" fill="none">
                            <path d="M1 3l2 2 4-4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </span>
                      {/* Index + label */}
                      <span style={{ display: 'flex', flexDirection: 'column', gap: '0.1rem' }}>
                        <span style={{ fontSize: '0.6rem', color: done ? '#444' : '#7B61FF', fontFamily: 'IBM Plex Mono, monospace', opacity: done ? 0.5 : 0.7, transition: 'color 0.15s ease' }}>
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        <span style={{ fontSize: '0.72rem', color: done ? '#444' : '#aaa', lineHeight: 1.35, textDecoration: done ? 'line-through' : 'none', transition: 'color 0.15s ease' }}>
                          {a.title || a.action}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div style={{ marginTop: 'auto', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <Link
              to="/"
              className="ops-navbar-cta"
              style={{ textAlign: 'center', display: 'block', textDecoration: 'none' }}
            >
              Dashboard
            </Link>
            {onRestart && (
              <button
                onClick={onRestart}
                style={{
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontSize: '0.6rem',
                  letterSpacing: '0.14em',
                  textTransform: 'uppercase',
                  background: 'transparent',
                  color: '#555',
                  border: '1px solid #222',
                  borderRadius: '999px',
                  padding: '0.4rem 1rem',
                  cursor: 'pointer',
                  transition: 'color 0.18s ease, border-color 0.18s ease',
                  width: '100%',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = '#c8922a';
                  (e.currentTarget as HTMLButtonElement).style.borderColor = '#c8922a44';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = '#555';
                  (e.currentTarget as HTMLButtonElement).style.borderColor = '#222';
                }}
              >
                ↺ Restart
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="chat-main">
          <div className="chat-messages">
            {messages.length === 0 && !isStreaming ? (
              <div className="chat-empty">
                <div className="chat-empty-glyph">◈</div>
                <div className="chat-empty-text">
                  Ask where revenue is slipping, which lead needs attention, or what Theo should protect this week.
                </div>
                <div className="chat-empty-prompts">
                  <button type="button" className="chat-empty-prompt" onClick={() => setInput('Which lead is most likely to stall unless Theo follows up today?')}>
                    Find the cooling lead
                  </button>
                  <button type="button" className="chat-empty-prompt" onClick={() => setInput('What should Theo do this week to protect both delivery and cash flow?')}>
                    Protect delivery and cash flow
                  </button>
                  <button type="button" className="chat-empty-prompt" onClick={() => setInput('How are the proactive and reactive agents helping right now?')}>
                    Explain the agent system
                  </button>
                </div>
              </div>
            ) : (
              messages.map((message, msgIndex) => (
                <div
                  key={message.id}
                  className={`msg msg--${message.role}`}
                >
                  <div className="msg-meta">
                    <span className={`msg-role msg-role--${message.role}`}>
                      {message.role === 'user' ? 'You' : 'Oracle'}
                    </span>
                    {message.role === 'assistant' && intent && msgIndex === messages.length - 1 && INTENT_COLORS[intent] && (
                      <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded border ${INTENT_COLORS[intent]}`}>
                        {intent}
                      </span>
                    )}
                    <span className="msg-line" />
                  </div>
                  <div className="msg-body">
                    {message.parts.map((part, i) =>
                      part.type === 'text' ? (
                        <MemoizedMarkdown key={i} id={`${message.id}-${i}`} content={part.text} />
                      ) : null
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
              <label className="chat-input-label" htmlFor="chat-input" style={{ display: 'block', marginBottom: '0.5rem' }}>
                Your query · shift+enter for newline
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div className="chat-input-wrap">
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
              </div>{/* end row */}
            </form>
          </div>
        </div>{/* end chat-main */}
      </div>{/* end chat-layout */}
    </div>
  );
}
