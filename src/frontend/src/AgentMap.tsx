import { useEffect, useMemo, useState } from 'react';

interface AgentMapNode {
  id: string;
  label: string;
  type: 'master' | 'worker';
  status: string;
  queue_depth: number;
  last_error?: string | null;
}

interface ApprovalItem {
  approval_id: string;
  task_id: string;
  worker_id: string;
  reason: string;
}

interface AgentMapResponse {
  active_scenario: {
    scenario_id: string;
    title: string;
  } | null;
  nodes: AgentMapNode[];
  edges: { from: string; to: string }[];
  approvals: ApprovalItem[];
  recent_events: { event_id: string; type: string; payload: Record<string, unknown>; created_at: string }[];
  updated_at: string;
}

interface SkillInfo {
  skill_id: string;
  display_name: string;
  actions: { name: string; risk: string }[];
}

const STATUS_CLASSES: Record<string, string> = {
  ready: 'agent-map-status--ready',
  running: 'agent-map-status--running',
  degraded: 'agent-map-status--degraded',
  open_circuit: 'agent-map-status--open',
};

export default function AgentMap() {
  const [data, setData] = useState<AgentMapResponse | null>(null);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [phase, setPhase] = useState<'loading' | 'ready' | 'error'>('loading');
  const [events, setEvents] = useState<Array<{ type: string; created_at: string }>>([]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const res = await fetch('/api/agent/map');
        const body = (await res.json()) as AgentMapResponse;
        if (!cancelled) {
          setData(body);
          setPhase('ready');
        }
        try {
          const skillsRes = await fetch('/api/agent/skills');
          const skillsBody = (await skillsRes.json()) as { skills: SkillInfo[] };
          if (!cancelled) {
            setSkills(skillsBody.skills ?? []);
          }
        } catch {
          if (!cancelled) {
            setSkills([]);
          }
        }
      } catch {
        if (!cancelled) {
          setPhase('error');
        }
      }
    };

    load();
    const id = window.setInterval(load, 5000);

    const source = new EventSource('/api/agent/stream');
    source.onmessage = (msg) => {
      try {
        const payload = JSON.parse(msg.data) as { type?: string; created_at?: string };
        if (payload.type && payload.created_at) {
          setEvents((prev) => [{ type: payload.type!, created_at: payload.created_at! }, ...prev].slice(0, 8));
          load();
        }
      } catch {
        // no-op
      }
    };

    source.onerror = () => {
      source.close();
    };

    return () => {
      cancelled = true;
      window.clearInterval(id);
      source.close();
    };
  }, []);

  const workers = useMemo(() => data?.nodes.filter((n) => n.type === 'worker') ?? [], [data]);

  const resolveApproval = async (approvalId: string, decision: 'approved' | 'rejected') => {
    try {
      await fetch('/api/agent/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_id: approvalId, decision }),
      });
    } finally {
      const res = await fetch('/api/agent/map');
      const body = (await res.json()) as AgentMapResponse;
      setData(body);
    }
  };

  return (
    <section className="agent-map-panel">
      <div className="agent-map-header">
        <span className="agent-map-title">Agent Map</span>
        {phase === 'loading' && <span className="agent-map-meta">syncing...</span>}
        {phase === 'ready' && <span className="agent-map-meta">updated {new Date(data?.updated_at || '').toLocaleTimeString()}</span>}
        {phase === 'error' && <span className="agent-map-meta agent-map-meta--error">unavailable</span>}
      </div>

      {data?.active_scenario && (
        <div className="agent-map-scenario">Active scenario: {data.active_scenario.title}</div>
      )}

      <div className="agent-map-grid">
        {workers.map((worker) => (
          <div key={worker.id} className="agent-map-node">
            <div className="agent-map-node-row">
              <span className="agent-map-node-name">{worker.label}</span>
              <span className={`agent-map-status ${STATUS_CLASSES[worker.status] || ''}`}>{worker.status}</span>
            </div>
            <div className="agent-map-node-meta">Queue: {worker.queue_depth}</div>
            {worker.last_error && <div className="agent-map-node-error">{worker.last_error}</div>}
          </div>
        ))}
      </div>

      {data && data.approvals.length > 0 && (
        <div className="agent-map-approvals">
          <div className="agent-map-approval-title">Pending approvals</div>
          {data.approvals.map((approval) => (
            <div key={approval.approval_id} className="agent-map-approval-item">
              <div>{approval.worker_id}: {approval.reason}</div>
              <div className="agent-map-approval-actions">
                <button type="button" className="agent-map-btn agent-map-btn--approve" onClick={() => resolveApproval(approval.approval_id, 'approved')}>
                  Approve
                </button>
                <button type="button" className="agent-map-btn agent-map-btn--reject" onClick={() => resolveApproval(approval.approval_id, 'rejected')}>
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="agent-map-events">
        <div className="agent-map-events-title">Recent runtime events</div>
        {events.length === 0 ? (
          <div className="agent-map-events-empty">No events yet</div>
        ) : (
          events.map((evt, idx) => (
            <div key={`${evt.created_at}-${idx}`} className="agent-map-event-item">
              <span>{evt.type}</span>
              <span>{new Date(evt.created_at).toLocaleTimeString()}</span>
            </div>
          ))
        )}
      </div>

      {skills.length > 0 && (
        <div className="agent-map-events">
          <div className="agent-map-events-title">Skill contracts</div>
          {skills.map((skill) => (
            <div key={skill.skill_id} className="agent-map-event-item">
              <span>{skill.display_name}</span>
              <span>{skill.actions.length} actions</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
