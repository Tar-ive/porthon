import { useCallback, useEffect, useRef, useState } from 'react';
import ActionCard from '../components/ActionCard';
import { useAgentStream } from '../hooks/useAgentStream';

interface Scenario {
  id: string;
  title: string;
  horizon: string;
  likelihood: string;
  summary: string;
  tags: string[];
}

interface Props {
  scenario: Scenario | null;
  onContinue: () => void;
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

const DEMO_AUTH_HEADER = {
  'Content-Type': 'application/json',
  Authorization: 'Bearer sk_demo_default',
};

const TOOL_STRIP = [
  { icon: '◈', label: 'Google Calendar', status: 'blocks queued', iconColor: '#38BDF8' },
  { icon: '≋', label: 'Notion', status: 'Pipeline ready', iconColor: '#ffffff' },
  { icon: 'Ω', label: 'Figma', status: '1 challenge scoped', iconColor: '#7B61FF' },
];

function SkeletonCard() {
  return (
    <div
      style={{
        border: '1px solid #2a2a3a',
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '0.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
      }}
    >
      <div style={{ width: '2rem', height: '14px', background: '#1e1e2e', borderRadius: '4px', flexShrink: 0 }} />
      <div style={{ width: '1rem', height: '14px', background: '#1e1e2e', borderRadius: '4px', flexShrink: 0 }} />
      <div style={{ flex: 1, height: '14px', background: '#1e1e2e', borderRadius: '4px' }} />
      <div style={{ width: '80px', height: '14px', background: '#1e1e2e', borderRadius: '4px', flexShrink: 0 }} />
    </div>
  );
}

export default function ActionsScreen({ scenario, onContinue }: Props) {
  const [actions, setActions] = useState<Action[]>([]);
  const [phase, setPhase] = useState<'loading' | 'ready' | 'error'>('loading');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [activating, setActivating] = useState(false);
  const [refreshBanner, setRefreshBanner] = useState(false);

  const { isAnalyzing, actionsVersion } = useAgentStream();
  const prevActionsVersion = useRef(0);

  const fetchActions = useCallback(async () => {
    if (!scenario) return;
    setPhase('loading');
    try {
      const res = await fetch('/v1/actions', {
        method: 'POST',
        headers: DEMO_AUTH_HEADER,
        body: JSON.stringify({ scenario_id: scenario.id }),
      });
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      const list: Action[] = Array.isArray(data) ? data : (data?.data ?? []);
      setActions(list);
      setPhase('ready');
      // Persist for chat context injection
      sessionStorage.setItem('appActions', JSON.stringify(list));
    } catch {
      setPhase('error');
    }
  }, [scenario]);

  // Initial fetch
  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  // Auto-refresh when actionsVersion increments
  useEffect(() => {
    if (actionsVersion !== prevActionsVersion.current) {
      prevActionsVersion.current = actionsVersion;
      setRefreshBanner(true);
      fetchActions().then(() => {
        setTimeout(() => setRefreshBanner(false), 3000);
      });
    }
  }, [actionsVersion, fetchActions]);

  const handleDeploy = async () => {
    if (!scenario) return;
    setActivating(true);

    // Fire-and-forget activate call
    fetch('/api/agent/activate', {
      method: 'POST',
      headers: DEMO_AUTH_HEADER,
      body: JSON.stringify({
        scenario_id: scenario.id,
        scenario_title: scenario.title,
        scenario_summary: scenario.summary,
        scenario_horizon: scenario.horizon,
        scenario_likelihood: scenario.likelihood,
        scenario_tags: scenario.tags,
      }),
    }).catch(() => {});

    setTimeout(() => {
      onContinue();
    }, 1500);
  };

  const horizonLabel = scenario?.horizon
    ? scenario.horizon.charAt(0).toUpperCase() + scenario.horizon.slice(1)
    : '';

  return (
    <div
      style={{
        background: '#0a0a0f',
        minHeight: '100vh',
        color: '#fff',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        overflowY: 'auto',
        padding: '2rem 1rem',
      }}
    >
      <div style={{ width: '100%', maxWidth: '800px' }}>
        {/* Live update banners */}
        {refreshBanner && (
          <div
            style={{
              background: '#1a1410',
              border: '1px solid #F59E0B44',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
              marginBottom: '1rem',
              color: '#F59E0B',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: '#F59E0B',
                display: 'inline-block',
                flexShrink: 0,
              }}
            />
            New data detected — refreshing your plan...
          </div>
        )}

        {isAnalyzing && !refreshBanner && (
          <div
            style={{
              background: '#1a1410',
              border: '1px solid #F59E0B44',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
              marginBottom: '1rem',
              color: '#F59E0B',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: '#F59E0B',
                display: 'inline-block',
                flexShrink: 0,
                animation: 'pulse 1.5s ease-in-out infinite',
              }}
            />
            Analyzing new data...
          </div>
        )}

        {/* Header */}
        <div style={{ marginBottom: '2rem' }}>
          {scenario && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.75rem',
              }}
            >
              <span
                style={{
                  fontSize: '0.8rem',
                  color: '#888',
                  background: '#1a1a2a',
                  border: '1px solid #2a2a3a',
                  borderRadius: '4px',
                  padding: '2px 8px',
                  maxWidth: '320px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {scenario.title}
              </span>
              <span
                style={{
                  fontSize: '0.75rem',
                  color: '#7B61FF',
                  background: '#7B61FF18',
                  border: '1px solid #7B61FF44',
                  borderRadius: '4px',
                  padding: '2px 8px',
                }}
              >
                {horizonLabel}
              </span>
            </div>
          )}

          <h1
            style={{
              fontSize: '2rem',
              fontWeight: 700,
              margin: '0 0 0.4rem 0',
              color: '#ffffff',
              lineHeight: 1.2,
            }}
          >
            Your week, planned
          </h1>
          <p style={{ color: '#666', margin: 0, fontSize: '0.95rem' }}>
            10 concrete actions mapped to your patterns and questline
          </p>

          {isAnalyzing && (
            <div
              style={{
                marginTop: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                color: '#F59E0B',
                fontSize: '0.8rem',
              }}
            >
              <span
                style={{
                  width: '5px',
                  height: '5px',
                  borderRadius: '50%',
                  background: '#F59E0B',
                  display: 'inline-block',
                }}
              />
              Updating...
            </div>
          )}
        </div>

        {/* Action list */}
        <div style={{ marginBottom: '1.5rem' }}>
          {phase === 'loading' &&
            Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)}

          {phase === 'error' && (
            <div
              style={{
                color: '#888',
                fontSize: '0.9rem',
                padding: '1rem',
                background: '#1a1a2a',
                border: '1px solid #2a2a3a',
                borderRadius: '8px',
                textAlign: 'center',
              }}
            >
              Could not load actions — using cached plan
            </div>
          )}

          {phase === 'ready' &&
            actions.map((action, i) => (
              <ActionCard
                key={action.id}
                action={action}
                index={i}
                expanded={expandedId === action.id}
                onToggle={() =>
                  setExpandedId((prev) => (prev === action.id ? null : action.id))
                }
              />
            ))}

          {phase === 'ready' && actions.length === 0 && (
            <div
              style={{
                color: '#555',
                fontSize: '0.9rem',
                padding: '2rem',
                textAlign: 'center',
              }}
            >
              No actions generated yet.
            </div>
          )}
        </div>

        {/* Tool integration strip */}
        <div
          style={{
            display: 'flex',
            gap: '0.75rem',
            marginBottom: '2rem',
            flexWrap: 'wrap',
          }}
        >
          {TOOL_STRIP.map((tool) => (
            <div
              key={tool.label}
              style={{
                flex: '1 1 0',
                minWidth: '140px',
                background: '#0f0f1a',
                border: '1px solid #2a2a3a',
                borderRadius: '8px',
                padding: '0.75rem 1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span
                style={{
                  fontSize: '1rem',
                  color: tool.iconColor,
                  fontFamily: 'monospace',
                  flexShrink: 0,
                }}
              >
                {tool.icon}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: '0.8rem',
                    color: '#ccc',
                    fontWeight: 500,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {tool.label}
                </div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: '#555',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {tool.status}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Deploy button */}
        <button
          onClick={handleDeploy}
          disabled={activating}
          className="ops-navbar-cta"
          style={{
            width: '100%',
            padding: '14px 32px',
            borderRadius: '10px',
            cursor: activating ? 'not-allowed' : 'pointer',
            fontSize: '0.7rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            opacity: activating ? 0.7 : 1,
          }}
        >
          {activating ? (
            <>
              <span
                style={{
                  width: '14px',
                  height: '14px',
                  border: '2px solid #ffffff44',
                  borderTop: '2px solid #fff',
                  borderRadius: '50%',
                  display: 'inline-block',
                  animation: 'spin 0.7s linear infinite',
                }}
              />
              Activating...
            </>
          ) : (
            'Deploy Agents'
          )}
        </button>

        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }
        `}</style>
      </div>
    </div>
  );
}
