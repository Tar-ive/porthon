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
  tasks?: Array<{
    task_id: string;
    worker_id: string;
    action: string;
    status: string;
    result_summary?: string | null;
    external_links?: Record<string, string>;
    updated_at: string;
  }>;
  workflow_state?: Record<string, unknown>;
  demo_artifacts?: Record<string, unknown>;
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
  const recentTasks = useMemo(() => (data?.tasks ?? []).slice(-8).reverse(), [data]);
  const integrationLinks = useMemo(() => {
    const artifacts = data?.demo_artifacts ?? {};
    const links = (artifacts['integration_links'] as Record<string, unknown> | undefined) ?? {};
    const out: Array<{ label: string; href: string }> = [];
    for (const [k, v] of Object.entries(links)) {
      if (Array.isArray(v)) {
        for (const item of v) {
          if (typeof item === 'string' && item) {
            out.push({ label: k, href: item });
          }
        }
      } else if (typeof v === 'string' && v) {
        out.push({ label: k, href: v });
      }
    }
    return out.slice(0, 8);
  }, [data]);
  const figmaPending = useMemo(() => {
    const artifacts = data?.demo_artifacts ?? {};
    const figmaWatch = (artifacts['figma_watch'] as Record<string, unknown> | undefined) ?? {};
    const pending = (figmaWatch['pending_items'] as Array<Record<string, unknown>> | undefined) ?? [];
    return pending.slice(-4).reverse();
  }, [data]);

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

      {recentTasks.length > 0 && (
        <div className="agent-map-events">
          <div className="agent-map-events-title">Recent task outcomes</div>
          {recentTasks.map((task) => (
            <div key={task.task_id} className="agent-map-event-item">
              <span>{task.worker_id}.{task.action} · {task.status}</span>
              <span>{task.result_summary || new Date(task.updated_at).toLocaleTimeString()}</span>
            </div>
          ))}
        </div>
      )}

      {figmaPending.length > 0 && (
        <div className="agent-map-events">
          <div className="agent-map-events-title">Figma watch pending</div>
          {figmaPending.map((item, idx) => (
            <div key={`${String(item['event_id'] || idx)}`} className="agent-map-event-item">
              <span>{String(item['summary'] || item['message'] || 'Pending item')}</span>
              <span>{String(item['status'] || 'ready_to_send')}</span>
            </div>
          ))}
        </div>
      )}

      {integrationLinks.length > 0 && (
        <div className="agent-map-events">
          <div className="agent-map-events-title">Integration links</div>
          {integrationLinks.map((link, idx) => (
            <a
              key={`${link.href}-${idx}`}
              className="agent-map-event-item"
              href={link.href}
              target="_blank"
              rel="noreferrer"
            >
              <span>{link.label}</span>
              <span>open</span>
            </a>
          ))}
        </div>
      )}
    </section>
  );
}
