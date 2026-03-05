import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useEffect, useRef, useState } from 'react';
import ChatSidebar from './components/ChatSidebar';
import { MemoizedMarkdown } from './MemoizedMarkdown';

interface Scenario {
  id: string;
  title: string;
  horizon: string;
  likelihood: string;
  summary: string;
  tags: string[];
}

interface Quest {
  action: string;
  rationale: string;
  data_ref: string;
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

export default function Chat({ scenario }: { scenario: Scenario }) {
  const [input, setInput] = useState('');
  const [intent, setIntent] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const intentRef = useRef(setIntent);
  intentRef.current = setIntent;

  // Quest state
  const [quests, setQuests] = useState<Quest[]>([]);
  const [questsPhase, setQuestsPhase] = useState<'loading' | 'ready' | 'error'>('loading');
  const [questsCollapsed, setQuestsCollapsed] = useState(false);
  const [expandedQuest, setExpandedQuest] = useState<string | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState<string>('');
  const [workflowBusy, setWorkflowBusy] = useState<'proactive' | 'figma' | null>(null);

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
    }).catch(() => {
      // Agent map will show unavailable if activation fails.
    });

    setQuestsPhase('loading');
    fetch('/api/actions', {
      method: 'POST',
      headers: DEMO_JSON_HEADERS,
      body: JSON.stringify({
        scenario_id: scenario.id,
        scenario_title: scenario.title,
        scenario_summary: scenario.summary,
        scenario_horizon: scenario.horizon,
        scenario_likelihood: scenario.likelihood,
      }),
    })
      .then((r) => r.json())
      .then((data) => {
        setQuests(data.actions || []);
        setQuestsPhase('ready');
      })
      .catch(() => setQuestsPhase('error'));
  }, [scenario.horizon, scenario.id, scenario.likelihood, scenario.summary, scenario.title]);

  const [transport] = useState(
    () =>
      new DefaultChatTransport({
        api: '/api/chat',
        body: { scenario },
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

  const postDemoEvent = async (type: string, payload: Record<string, unknown>) => {
    const res = await fetch('/v1/events', {
      method: 'POST',
      headers: DEMO_JSON_HEADERS,
      body: JSON.stringify({ type, payload }),
    });
    if (!res.ok) {
      throw new Error(`Failed: ${type}`);
    }
    return res.json();
  };

  const runProactiveWorkflow = async () => {
    setWorkflowBusy('proactive');
    setWorkflowStatus('Running proactive workflow...');
    try {
      await postDemoEvent('demo.workflow.proactive.preview', {});
      const commit = await postDemoEvent('demo.workflow.proactive.commit', {});
      const duration = commit?.cycle?.cycle_duration_ms;
      setWorkflowStatus(
        duration ? `Proactive workflow complete (${duration}ms cycle).` : 'Proactive workflow complete.'
      );
    } catch {
      setWorkflowStatus('Proactive workflow failed. Check /v1/events.');
    } finally {
      setWorkflowBusy(null);
    }
  };

  const runFigmaWorkflow = async () => {
    setWorkflowBusy('figma');
    setWorkflowStatus('Running figma watch workflow...');
    try {
      await postDemoEvent('demo.workflow.figma_watch.start', {
        file_key: 'demo_file_123',
        demo_mode: false,
      });
      await fetch('/v1/integrations/composio/webhook', {
        method: 'POST',
        headers: DEMO_JSON_HEADERS,
        body: JSON.stringify({
          id: 'ui_wh_001',
          event_id: 'ui_wh_001',
          comment_id: 'ui_comment_001',
          file_key: 'demo_file_123',
          message: 'Can we simplify this frame hierarchy?',
          from: { name: 'Teammate' },
          created_at: new Date().toISOString(),
        }),
      });
      setWorkflowStatus('Figma watch workflow complete. Pending items updated.');
    } catch {
      setWorkflowStatus('Figma workflow failed. Check /v1/events.');
    } finally {
      setWorkflowBusy(null);
    }
  };

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
        </div>
        <div className="chat-header-dot" />
      </header>

      {/* Quests Panel */}
      <div className={`quests-panel${questsCollapsed ? '' : ' quests-panel--expanded'}`}>
        <div
          className="quests-panel-header"
          onClick={() => setQuestsCollapsed(!questsCollapsed)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && setQuestsCollapsed(!questsCollapsed)}
        >
          <span className="quests-panel-icon">◈</span>
          <span className="quests-panel-title">Recommended Quests</span>
          {questsPhase === 'loading' && (
            <span className="quests-loading-rune" style={{ fontSize: '0.75rem' }}>✦</span>
          )}
          {questsPhase === 'ready' && quests.length > 0 && (
            <span className="quests-panel-count">{quests.length} actions</span>
          )}
          <span className="quests-panel-toggle">{questsCollapsed ? '▼' : '▲'}</span>
        </div>

        {!questsCollapsed && (
          <div className="quests-body">
            {questsPhase === 'loading' && (
              <div className="quests-loading">
                <span className="quests-loading-rune">✦</span>
                <span className="quests-loading-text">Generating quest recommendations…</span>
              </div>
            )}
            {questsPhase === 'error' && (
              <div className="quests-loading">
                <span className="quests-loading-text quests-loading-text--error">
                  Could not load quests — try chatting directly
                </span>
              </div>
            )}
            {questsPhase === 'ready' &&
              quests.map((q, i) => {
                const key = `q${i}`;
                const isExpanded = expandedQuest === key;
                return (
                  <div
                    key={key}
                    className={`quest-card${isExpanded ? ' quest-card--expanded' : ''}`}
                    style={{ animationDelay: `${i * 0.08}s` }}
                  >
                    <div
                      className="quest-card-main"
                      onClick={() => setExpandedQuest(isExpanded ? null : key)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === 'Enter' && setExpandedQuest(isExpanded ? null : key)}
                    >
                      <span className="quest-card-num">Q{String(i + 1).padStart(2, '0')}</span>
                      <span className="quest-card-action">{q.action}</span>
                      {q.data_ref && <span className="quest-card-ref">{q.data_ref}</span>}
                    </div>
                    {isExpanded && (
                      <div className="quest-card-detail">
                        <div>
                          <div className="quest-detail-label">Rationale</div>
                          <div className="quest-detail-text">{q.rationale}</div>
                        </div>
                        {q.compound_summary && (
                          <div>
                            <div className="quest-detail-label">Compounds to</div>
                            <div className="quest-detail-text">{q.compound_summary}</div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        )}
      </div>

      <div className="workflow-strip">
        <div className="workflow-strip-title">Demo Workflows</div>
        <div className="workflow-strip-actions">
          <button
            type="button"
            className="workflow-btn"
            onClick={runProactiveWorkflow}
            disabled={workflowBusy !== null}
          >
            {workflowBusy === 'proactive' ? 'Running...' : 'Run Proactive'}
          </button>
          <button
            type="button"
            className="workflow-btn"
            onClick={runFigmaWorkflow}
            disabled={workflowBusy !== null}
          >
            {workflowBusy === 'figma' ? 'Running...' : 'Run Figma Watch'}
          </button>
        </div>
        {workflowStatus && <div className="workflow-strip-status">{workflowStatus}</div>}
      </div>

      {/* Left sidebar + Main chat split */}
      <div className="chat-layout">
        <ChatSidebar quests={quests} />

        {/* Messages */}
        <div className="chat-main">
          <div className="chat-messages">
            {messages.length === 0 && !isStreaming ? (
              <div className="chat-empty">
                <div className="chat-empty-glyph">◈</div>
                <div className="chat-empty-text">Begin your inquiry</div>
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
        </div>{/* end chat-main */}
      </div>{/* end chat-layout */}
    </div>
  );
}
