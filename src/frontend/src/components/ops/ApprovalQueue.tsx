import { useCallback, useEffect, useState } from 'react';
import { useAgentStream } from '../../hooks/useAgentStream';

interface Approval {
    id?: string;
    approval_id?: string;
    task_id: string;
    worker_id: string;
    reason: string;
    decision?: string | null;
    resolved_at?: string | null;
}

const DEMO_TOKEN = 'Bearer sk_demo_default';

export default function ApprovalQueue() {
    const [approvals, setApprovals] = useState<Approval[]>([]);
    const [phase, setPhase] = useState<'loading' | 'ready' | 'error'>('loading');
    const { lastEvent } = useAgentStream();

    const load = useCallback(async () => {
        try {
            const res = await fetch('/v1/approvals', {
                headers: { Authorization: DEMO_TOKEN },
            });
            const body = await res.json();
            const data = body?.data ?? body?.approvals ?? [];
            setApprovals(data);
            setPhase('ready');
        } catch {
            setPhase('error');
        }
    }, []);

    // Initial load + periodic poll
    useEffect(() => {
        load();
        const poll = setInterval(load, 10000);
        return () => clearInterval(poll);
    }, [load]);

    // Refresh on any SSE event (shared connection via context, no extra SSE)
    useEffect(() => {
        if (lastEvent) load();
    }, [lastEvent, load]);

    const resolve = async (approvalId: string, decision: 'approved' | 'rejected') => {
        try {
            await fetch(`/v1/approvals/${approvalId}/resolve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: DEMO_TOKEN,
                },
                body: JSON.stringify({ decision }),
            });
            load();
        } catch {
            // silent
        }
    };

    const pending = approvals.filter((a) => !a.decision);

    return (
        <div className="ops-panel approval-queue">
            <div className="ops-panel-header">
                <span className="ops-panel-title">Approval Queue</span>
                {pending.length > 0 && (
                    <span className="ops-panel-badge" style={{ color: '#fcd34d' }}>
                        {pending.length} pending
                    </span>
                )}
            </div>
            <div className="ops-panel-body">
                {phase === 'loading' && <div className="approval-empty">Loading…</div>}
                {phase === 'error' && (
                    <div className="approval-empty" style={{ color: '#fca5a5' }}>Unavailable</div>
                )}
                {phase === 'ready' && pending.length === 0 && (
                    <div className="approval-empty">✓ No pending approvals</div>
                )}
                {phase === 'ready' && pending.map((a) => {
                    const aid = a.id || a.approval_id || '';
                    return (
                        <div key={aid} className="approval-item">
                            <div className="approval-reason">{a.reason}</div>
                            <div className="approval-worker">{a.worker_id}</div>
                            <div className="approval-actions">
                                <button
                                    className="approval-btn approval-btn--approve"
                                    onClick={() => resolve(aid, 'approved')}
                                >
                                    Approve
                                </button>
                                <button
                                    className="approval-btn approval-btn--reject"
                                    onClick={() => resolve(aid, 'rejected')}
                                >
                                    Reject
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
