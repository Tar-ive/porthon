import { useEffect, useRef, useState } from 'react';

interface FeedEvent {
    type: string;
    payload?: Record<string, unknown>;
    created_at?: string;
}

export default function TelemetryFeed() {
    const [events, setEvents] = useState<FeedEvent[]>([]);
    const sseRef = useRef<EventSource | null>(null);

    useEffect(() => {
        const source = new EventSource('/v1/events/stream');
        sseRef.current = source;

        source.onmessage = (msg) => {
            try {
                const data = JSON.parse(msg.data) as FeedEvent;
                if (data.type) {
                    setEvents((prev) => [data, ...prev].slice(0, 50));
                }
            } catch {
                // skip non-JSON keepalives
            }
        };

        source.onerror = () => {
            source.close();
        };

        return () => {
            source.close();
        };
    }, []);

    const formatTime = (ts?: string) => {
        if (!ts) return '--:--';
        try {
            return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch {
            return '--:--';
        }
    };

    const summarizePayload = (payload?: Record<string, unknown>) => {
        if (!payload || Object.keys(payload).length === 0) return '';
        const entries = Object.entries(payload).slice(0, 3);
        return entries.map(([k, v]) => `${k}=${typeof v === 'object' ? '…' : String(v)}`).join(' ');
    };

    return (
        <div className="ops-panel telemetry-feed">
            <div className="ops-panel-header">
                <span className="ops-panel-title">
                    Telemetry Feed <span className="feed-cursor" />
                </span>
                <span className="telemetry-live-dot" />
                <span className="ops-panel-badge">live</span>
            </div>
            <div className="ops-panel-body">
                {events.length === 0 ? (
                    <div className="feed-empty">Awaiting events…</div>
                ) : (
                    events.map((evt, idx) => (
                        <div key={`${evt.created_at}-${idx}`} className="feed-event">
                            <span className="feed-ts">{formatTime(evt.created_at)}</span>
                            <span className="feed-type">[{evt.type}]</span>
                            <span className="feed-payload">{summarizePayload(evt.payload)}</span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
