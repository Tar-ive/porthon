import { useEffect, useRef, useState } from 'react';

interface FeedEvent {
    type: string;
    payload?: Record<string, unknown>;
    created_at?: string;
}

const EVENT_META: Record<string, { glyph: string; cls: string; label: string }> = {
    data_changed:      { glyph: '◆', cls: 'feed-event--data',      label: 'data changed'      },
    analysis_running:  { glyph: '◈', cls: 'feed-event--analyzing', label: 'analyzing'         },
    scenarios_updated: { glyph: '✦', cls: 'feed-event--updated',   label: 'trajectories'      },
    actions_updated:   { glyph: '✦', cls: 'feed-event--updated',   label: 'actions'           },
    analysis_stable:   { glyph: '·', cls: 'feed-event--stable',    label: 'stable'            },
    analysis_error:    { glyph: '✗', cls: 'feed-event--error',     label: 'error'             },
    cycle_start:       { glyph: '▶', cls: 'feed-event--cycle',     label: 'cycle start'       },
    cycle_end:         { glyph: '■', cls: 'feed-event--cycle',     label: 'cycle end'         },
    task_completed:    { glyph: '✓', cls: 'feed-event--done',      label: 'task done'         },
    approval_created:  { glyph: '!', cls: 'feed-event--approval',  label: 'approval needed'   },
    scenario_activated:{ glyph: '◉', cls: 'feed-event--activated', label: 'scenario activated'},
};

function describeEvent(evt: FeedEvent): string {
    const p = evt.payload ?? {};
    switch (evt.type) {
        case 'data_changed': {
            const domain = p.domain as string ?? '';
            const src = p.source as string ?? '';
            return src === 'demo_push'
                ? `${domain} — demo push received`
                : `${domain} file updated`;
        }
        case 'analysis_running': {
            return (p.message as string) ?? `running ${p.stage ?? ''}…`;
        }
        case 'scenarios_updated': {
            const n = p.count as number ?? 0;
            return `${n} trajectories regenerated`;
        }
        case 'actions_updated': {
            const n = p.count as number ?? 0;
            return `${n} actions refreshed`;
        }
        case 'analysis_stable': {
            const domain = p.domain as string ?? '';
            return `${domain} — inputs unchanged`;
        }
        case 'analysis_error':
            return (p.message as string) ?? 'analysis failed';
        case 'task_completed':
            return (p.task_id as string) ?? 'task completed';
        case 'scenario_activated':
            return (p.title as string) ?? 'scenario activated';
        default: {
            const entries = Object.entries(p).slice(0, 2);
            return entries.map(([k, v]) => `${k}=${String(v)}`).join(' ') || evt.type;
        }
    }
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
                    setEvents((prev) => [data, ...prev].slice(0, 60));
                }
            } catch {
                // skip non-JSON keepalives
            }
        };

        source.onerror = () => source.close();
        return () => source.close();
    }, []);

    const formatTime = (ts?: string) => {
        if (!ts) return '--:--';
        try {
            return new Date(ts).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            });
        } catch {
            return '--:--';
        }
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
                    events.map((evt, idx) => {
                        const meta = EVENT_META[evt.type] ?? {
                            glyph: '·',
                            cls: 'feed-event--default',
                            label: evt.type,
                        };
                        return (
                            <div
                                key={`${evt.created_at}-${idx}`}
                                className={`feed-event ${meta.cls}`}
                            >
                                <span className="feed-glyph">{meta.glyph}</span>
                                <span className="feed-ts">{formatTime(evt.created_at)}</span>
                                <span className="feed-type">{meta.label}</span>
                                <span className="feed-payload">{describeEvent(evt)}</span>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
