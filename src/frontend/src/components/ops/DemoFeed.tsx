import { useEffect, useRef, useState } from 'react';
import { useAgentStream } from '../../hooks/useAgentStream';

interface DemoEvent {
    slug: string;
    label: string;
    description: string;
    domain: string;
}

type PushState = 'idle' | 'pushing' | 'analyzing' | 'done';

const DOMAIN_GLYPH: Record<string, string> = {
    calendar: '◈',
    finance: '◆',
    transactions: '◆',
    social: '◉',
    lifelog: '◇',
};

const DOMAIN_LABEL: Record<string, string> = {
    calendar: 'calendar',
    finance: 'finance',
    transactions: 'finance',
    social: 'social',
    lifelog: 'lifelog',
};

export default function DemoFeed() {
    const [events, setEvents] = useState<DemoEvent[]>([]);
    const [states, setStates] = useState<Record<string, PushState>>({});
    const activeSlug = useRef<string | null>(null);

    const { isAnalyzing, scenariosVersion, actionsVersion, changedDomain, lastEvent } = useAgentStream();

    useEffect(() => {
        fetch('/api/agent/demo/events')
            .then((r) => r.json())
            .then((body) => setEvents(body.events ?? []))
            .catch(() => {});
    }, []);

    // When analysis starts after a push, move slug to 'analyzing'
    useEffect(() => {
        if (isAnalyzing && activeSlug.current) {
            setStates((s) => ({ ...s, [activeSlug.current!]: 'analyzing' }));
        }
    }, [isAnalyzing]);

    // Mark done when analysis completes — either scenarios updated, actions updated,
    // or analysis_stable (no LLM change needed). All mean the run finished.
    useEffect(() => {
        const type = lastEvent?.type;
        if (
            activeSlug.current &&
            (type === 'scenarios_updated' || type === 'actions_updated' || type === 'analysis_stable')
        ) {
            setStates((s) => ({ ...s, [activeSlug.current!]: 'done' }));
            activeSlug.current = null;
        }
    }, [scenariosVersion, actionsVersion, lastEvent]);

    const push = async (slug: string) => {
        const cur = states[slug] ?? 'idle';
        if (cur === 'pushing' || cur === 'analyzing') return;
        activeSlug.current = slug;
        setStates((s) => ({ ...s, [slug]: 'pushing' }));
        try {
            await fetch(`/api/agent/demo/push/${slug}`, { method: 'POST' });
        } catch {
            setStates((s) => ({ ...s, [slug]: 'idle' }));
            activeSlug.current = null;
        }
    };

    const statusIcon = (state: PushState) => {
        if (state === 'idle') return '→';
        if (state === 'pushing') return '…';
        if (state === 'analyzing') return '◈';
        return '✓';
    };

    return (
        <div className="ops-panel demo-feed">
            <div className="ops-panel-header">
                <span className="ops-panel-title">
                    Live Data Feed
                    <span className="feed-cursor" />
                </span>
                {isAnalyzing && changedDomain && (
                    <span className="demo-feed-badge demo-feed-badge--analyzing">
                        analyzing {changedDomain}…
                    </span>
                )}
                {!isAnalyzing && scenariosVersion > 0 && (
                    <span className="demo-feed-badge demo-feed-badge--done">
                        ↻ trajectories updated
                    </span>
                )}
            </div>
            <div className="ops-panel-body">
                <p className="demo-feed-hint">
                    Push a real-time data event — the daemon detects the change and re-runs analysis instantly.
                </p>
                {events.map((evt) => {
                    const state = states[evt.slug] ?? 'idle';
                    return (
                        <button
                            key={evt.slug}
                            className={`demo-event-card demo-event-card--${state}`}
                            onClick={() => push(evt.slug)}
                            disabled={state === 'pushing' || state === 'analyzing'}
                        >
                            <div className="demo-event-left">
                                <span className="demo-event-glyph">
                                    {DOMAIN_GLYPH[evt.domain] ?? '◇'}
                                </span>
                                <div className="demo-event-info">
                                    <div className="demo-event-label">{evt.label}</div>
                                    <div className="demo-event-desc">{evt.description}</div>
                                    <span className="demo-event-domain">
                                        {DOMAIN_LABEL[evt.domain] ?? evt.domain}
                                    </span>
                                </div>
                            </div>
                            <span className={`demo-event-status demo-event-status--${state}`}>
                                {statusIcon(state)}
                            </span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
