import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useEffect, useRef, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { MemoizedMarkdown } from './MemoizedMarkdown';
import { useAgentStream } from './hooks/useAgentStream';

// ── Voice recording hook ───────────────────────────────────────────
type VoiceState = 'idle' | 'recording' | 'transcribing' | 'error';

/** Send a blob to the transcription endpoint and stream tokens back.
 *  Calls onToken with accumulated text (replace mode).
 *  Returns the final accumulated string. Abortable via signal. */
async function streamTranscribe(
  blob: Blob,
  format: string,
  onToken: (accumulated: string) => void,
  signal?: AbortSignal,
): Promise<string> {
  const formData = new FormData();
  formData.append('audio', blob, `recording.${format}`);
  formData.append('format', format);

  const res = await fetch('/v1/voice/transcribe', {
    method: 'POST',
    headers: { Authorization: DEMO_TOKEN },
    body: formData,
    signal,
  });
  if (!res.ok) throw new Error(`Transcription ${res.status}`);

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');
  const decoder = new TextDecoder();
  let buffer = '';
  let accumulated = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const raw = line.slice(5).trim();
      if (raw === '[DONE]') break;
      try {
        const chunk = JSON.parse(raw) as { token?: string };
        if (chunk.token) {
          accumulated += chunk.token;
          onToken(accumulated);
        }
      } catch { /* skip malformed */ }
    }
  }
  return accumulated;
}

const TRANSCRIBE_INTERVAL_MS = 1500;

function useVoiceInput(onTranscript: (text: string, replace?: boolean) => void) {
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const transcribingRef = useRef(false);
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  /** Build a blob from all chunks collected so far */
  const buildBlob = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    const mime = recorder?.mimeType ?? 'audio/webm';
    return new Blob(chunksRef.current, { type: mime });
  }, []);

  /** Send accumulated audio for transcription (non-overlapping) */
  const transcribeNow = useCallback(async () => {
    if (transcribingRef.current) return;          // skip if previous still in-flight
    if (chunksRef.current.length === 0) return;   // nothing recorded yet
    transcribingRef.current = true;

    // Abort any lingering previous request
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const blob = buildBlob();
    const format = (mediaRecorderRef.current?.mimeType ?? '').includes('webm') ? 'webm' : 'wav';

    try {
      await streamTranscribe(
        blob, format,
        (acc) => onTranscriptRef.current(acc, true),
        ctrl.signal,
      );
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        console.warn('Live transcription chunk failed', err);
      }
    } finally {
      transcribingRef.current = false;
    }
  }, [buildBlob]);

  const startRecording = useCallback(async () => {
    setVoiceError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      // timeslice = 500ms so chunks accumulate quickly for periodic sends
      recorder.start(500);
      mediaRecorderRef.current = recorder;
      setVoiceState('recording');

      // Kick off periodic transcription while user is still speaking
      intervalRef.current = setInterval(() => { transcribeNow(); }, TRANSCRIBE_INTERVAL_MS);
    } catch {
      setVoiceError('Microphone access denied');
      setVoiceState('error');
    }
  }, [transcribeNow]);

  const stopRecording = useCallback(async () => {
    // Clear interval
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    // Abort in-flight partial transcription
    abortRef.current?.abort();
    abortRef.current = null;
    transcribingRef.current = false;

    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state !== 'recording') return;

    setVoiceState('transcribing');

    // Wait for recorder to fully stop so we get all chunks
    const blob = await new Promise<Blob>((resolve) => {
      recorder.addEventListener('stop', () => {
        streamRef.current?.getTracks().forEach(t => t.stop());
        streamRef.current = null;
        resolve(new Blob(chunksRef.current, { type: recorder.mimeType }));
      }, { once: true });
      recorder.stop();
    });

    const format = recorder.mimeType.includes('webm') ? 'webm' : 'wav';

    try {
      await streamTranscribe(
        blob, format,
        (acc) => onTranscriptRef.current(acc, true),
      );
      setVoiceState('idle');
    } catch (err) {
      setVoiceError(err instanceof Error ? err.message : 'Transcription failed');
      setVoiceState('error');
    }
  }, []);

  const cancel = useCallback(() => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    abortRef.current?.abort();
    abortRef.current = null;
    transcribingRef.current = false;
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state === 'recording') {
      recorder.ondataavailable = null;
      recorder.stop();
    }
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;
    setVoiceState('idle');
    setVoiceError(null);
  }, []);

  return { voiceState, voiceError, startRecording, stopRecording, cancel };
}

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

  // pendingVoicePrefix tracks what was in the input before recording started,
  // so streaming tokens replace only the transcription portion, not prior text.
  const voicePrefixRef = useRef('');
  const { voiceState, voiceError, startRecording, stopRecording, cancel: cancelVoice } = useVoiceInput(
    (transcript, replace) => {
      if (replace) {
        // Streaming: replace the transcription portion after the prefix
        const sep = voicePrefixRef.current ? ' ' : '';
        setInput(voicePrefixRef.current + sep + transcript);
      } else {
        setInput(prev => prev ? `${prev} ${transcript}` : transcript);
      }
    }
  );

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

              {/* Mic button */}
              {!isStreaming && (
                <button
                  type="button"
                  className={`chat-btn chat-btn--mic${voiceState === 'recording' ? ' chat-btn--mic-active' : ''}${voiceState === 'transcribing' ? ' chat-btn--mic-busy' : ''}`}
                  onClick={() => {
                    if (voiceState === 'idle' || voiceState === 'error') {
                      voicePrefixRef.current = input;
                      startRecording();
                    } else if (voiceState === 'recording') {
                      stopRecording();
                    } else {
                      cancelVoice();
                    }
                  }}
                  title={voiceState === 'recording' ? 'Stop recording' : voiceState === 'transcribing' ? 'Transcribing…' : voiceState === 'error' ? (voiceError ?? 'Error') : 'Voice input'}
                  disabled={voiceState === 'transcribing'}
                >
                  {voiceState === 'recording' ? (
                    /* Pulsing waveform bars while recording */
                    <span className="mic-wave">
                      <span /><span /><span /><span /><span />
                    </span>
                  ) : voiceState === 'transcribing' ? (
                    <span className="mic-spin">◌</span>
                  ) : voiceState === 'error' ? (
                    <span title={voiceError ?? ''}>✕</span>
                  ) : (
                    /* Microphone SVG icon */
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="9" y="2" width="6" height="11" rx="3" />
                      <path d="M5 10a7 7 0 0 0 14 0" />
                      <line x1="12" y1="19" x2="12" y2="23" />
                      <line x1="8" y1="23" x2="16" y2="23" />
                    </svg>
                  )}
                </button>
              )}

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
