import { useEffect, useState } from 'react';

interface ActivityItem {
    id: string;
    file: string;
    type: string;
    icon: string;
    status: string;
    chunks: number;
    content_length: number;
    processed_at: string | null;
}

const DEMO_TOKEN = 'Bearer sk_demo_default';

export default function RecentActivity() {
    const [items, setItems] = useState<ActivityItem[]>([]);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch('/v1/knowledge-graph/activity', {
                    headers: { Authorization: DEMO_TOKEN },
                });
                const body = await res.json();
                setItems(body.data || []);
            } catch {
                // silent
            }
        })();
    }, []);

    const formatTime = (ts: string | null) => {
        if (!ts) return '—';
        try {
            const d = new Date(ts);
            return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
                ' ' +
                d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch {
            return '—';
        }
    };

    return (
        <div className="ops-panel recent-activity">
            <div className="ops-panel-header">
                <span className="ops-panel-title">Recent Activity</span>
                <span className="ops-panel-badge">{items.length} docs</span>
            </div>
            <div className="ops-panel-body">
                {items.length === 0 ? (
                    <div className="feed-empty">No activity yet</div>
                ) : (
                    items.map((item) => (
                        <div key={item.id} className="activity-item">
                            <span className="activity-icon">{item.icon}</span>
                            <div className="activity-info">
                                <div className="activity-file">{item.file}</div>
                                <div className="activity-meta">
                                    {item.chunks} chunks · {(item.content_length / 1000).toFixed(1)}K chars
                                </div>
                            </div>
                            <div className="activity-right">
                                <span className="activity-status">✓ {item.status}</span>
                                <span className="activity-time">{formatTime(item.processed_at)}</span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
