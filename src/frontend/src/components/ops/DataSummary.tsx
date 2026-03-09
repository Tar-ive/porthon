import { useEffect, useState, useRef } from 'react';

interface SourceData {
    type: string;
    icon: string;
    file: string;
    chunks: number;
    content_length: number;
    status: string;
}

interface SummaryData {
    sources: SourceData[];
    totals: { docs: number; chunks: number; entities: number; relations: number };
}

const DEMO_TOKEN = 'Bearer sk_demo_default';

function CountUp({ target, duration = 1500 }: { target: number; duration?: number }) {
    const [current, setCurrent] = useState(0);
    const ref = useRef<HTMLSpanElement>(null);

    useEffect(() => {
        let start = 0;
        const startTime = performance.now();
        const step = (now: number) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            start = Math.floor(eased * target);
            setCurrent(start);
            if (progress < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }, [target, duration]);

    return <span ref={ref}>{current.toLocaleString()}</span>;
}

const SOURCE_LABELS: Record<string, string> = {
    email: 'Emails',
    calendar: 'Calendar',
    bank: 'Transactions',
    social: 'Social',
    lifelog: 'Lifelog',
    files: 'Files',
    conversations: 'Conversations',
    profile: 'Profile',
    consent: 'Consent',
};

export default function DataSummary() {
    const [data, setData] = useState<SummaryData | null>(null);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch('/v1/knowledge-graph/summary', {
                    headers: { Authorization: DEMO_TOKEN },
                });
                const body = await res.json();
                setData(body);
            } catch {
                // silent
            }
        })();
    }, []);

    if (!data) {
        return (
            <div className="data-summary">
                <div className="data-summary-loading">Loading data…</div>
            </div>
        );
    }

    // Filter to main sources (skip consent/profile)
    const mainSources = data.sources.filter(
        (s) => !['consent', 'profile'].includes(s.type)
    );

    return (
        <div className="data-summary">
            <div className="data-summary-header">
                <span className="ops-panel-title">Data Processed</span>
                <span className="ops-panel-badge">
                    <CountUp target={data.totals.chunks} /> chunks
                </span>
                <span className="ops-panel-badge">
                    <CountUp target={data.totals.entities} /> entities
                </span>
                <span className="ops-panel-badge">
                    <CountUp target={data.totals.relations} /> relations
                </span>
            </div>
            <div className="data-summary-cards">
                {mainSources.map((source) => (
                    <div key={source.file} className="data-card">
                        <span className="data-card-icon">{source.icon}</span>
                        <div className="data-card-info">
                            <div className="data-card-label">
                                {SOURCE_LABELS[source.type] || source.type}
                            </div>
                            <div className="data-card-stat">
                                <CountUp target={source.chunks} duration={1200} /> chunks ·{' '}
                                {(source.content_length / 1000).toFixed(1)}K chars
                            </div>
                        </div>
                        <span className="data-card-status">●</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
