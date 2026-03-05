import { useEffect, useState, useRef, useCallback } from 'react';

interface WorkerData {
    id: string;
    label: string;
    status: string;
    queue_depth: number;
    last_error?: string | null;
}

const WORKER_GLYPHS: Record<string, string> = {
    kg_worker: 'λ',
    calendar_worker: '◈',
    notion_leads_worker: 'Σ',
    notion_opportunity_worker: '≋',
    facebook_worker: '◉',
    figma_worker: 'Ω',
};

const DEMO_TOKEN = 'Bearer sk_demo_default';

export default function WorkerFleet() {
    const [workers, setWorkers] = useState<WorkerData[]>([]);
    const [phase, setPhase] = useState<'loading' | 'ready' | 'error'>('loading');
    const sseRef = useRef<EventSource | null>(null);

    const load = useCallback(async () => {
        try {
            const res = await fetch('/v1/workers?expand[]=skills', {
                headers: { Authorization: DEMO_TOKEN },
            });
            const body = await res.json();
            const data = body?.data ?? body?.nodes?.filter((n: any) => n.type === 'worker') ?? [];
            setWorkers(data);
            setPhase('ready');
        } catch {
            setPhase('error');
        }
    }, []);

    useEffect(() => {
        load();
        const poll = setInterval(load, 8000);

        // SSE for real-time events
        const source = new EventSource('/v1/events/stream');
        sseRef.current = source;
        source.onmessage = () => {
            load(); // refresh on any event
        };
        source.onerror = () => source.close();

        return () => {
            clearInterval(poll);
            source.close();
        };
    }, [load]);

    return (
        <div className="ops-panel worker-fleet">
            <div className="ops-panel-header">
                <span className="ops-panel-title">Worker Fleet</span>
                <span className="ops-panel-badge">{workers.length} active</span>
            </div>
            <div className="ops-panel-body">
                {phase === 'loading' && (
                    <div className="feed-empty">Syncing workers…</div>
                )}
                {phase === 'error' && (
                    <div className="feed-empty" style={{ color: '#fca5a5' }}>Unavailable</div>
                )}
                {phase === 'ready' && workers.map((w) => (
                    <div key={w.id} className="worker-card">
                        <div className="worker-avatar">
                            <span className="worker-avatar-ring" />
                            {WORKER_GLYPHS[w.id] || '◇'}
                        </div>
                        <div className="worker-info">
                            <div className="worker-name">{w.label}</div>
                            <div className="worker-meta">Queue: {w.queue_depth}</div>
                        </div>
                        <span className={`worker-status worker-status--${w.status}`}>
                            {w.status}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}
