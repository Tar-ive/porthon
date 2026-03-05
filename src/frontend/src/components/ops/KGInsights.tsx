import { useEffect, useState } from 'react';

interface KGNode {
    id: string;
    label: string;
    category: string;
    size: number;
}

interface KGData {
    nodes: KGNode[];
    meta: { total_nodes: number; total_edges: number };
}

const DEMO_TOKEN = 'Bearer sk_demo_default';

const CATEGORY_COLORS: Record<string, string> = {
    person: '#c8922a',
    tool: '#38BDF8',
    place: '#84CC16',
    financial: '#EF4444',
    concept: '#7B61FF',
};

const CATEGORY_LABELS: Record<string, string> = {
    person: 'People',
    tool: 'Tools',
    place: 'Places',
    financial: 'Financial',
    concept: 'Concepts',
};

export default function KGInsights() {
    const [data, setData] = useState<KGData | null>(null);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch('/v1/knowledge-graph', {
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
            <div className="ops-panel kg-insights">
                <div className="ops-panel-header">
                    <span className="ops-panel-title">Knowledge Graph</span>
                </div>
                <div className="ops-panel-body">
                    <div className="feed-empty">Loading…</div>
                </div>
            </div>
        );
    }

    // Top 10 entities by connection count
    const topEntities = [...data.nodes]
        .sort((a, b) => b.size - a.size)
        .slice(0, 10);

    // Category distribution
    const catCounts: Record<string, number> = {};
    for (const node of data.nodes) {
        catCounts[node.category] = (catCounts[node.category] || 0) + 1;
    }
    const totalNodes = data.nodes.length;
    const categories = Object.entries(catCounts)
        .sort(([, a], [, b]) => b - a);

    return (
        <div className="ops-panel kg-insights">
            <div className="ops-panel-header">
                <span className="ops-panel-title">Knowledge Graph</span>
                <span className="ops-panel-badge">{data.meta.total_nodes} nodes</span>
                <span className="ops-panel-badge">{data.meta.total_edges} edges</span>
            </div>
            <div className="ops-panel-body" style={{ padding: '0.6rem 0.9rem' }}>
                {/* Category distribution bars */}
                <div className="kg-categories">
                    {categories.map(([cat, count]) => (
                        <div key={cat} className="kg-cat-row">
                            <span
                                className="kg-cat-dot"
                                style={{ background: CATEGORY_COLORS[cat] || '#6B7A8D' }}
                            />
                            <span className="kg-cat-label">
                                {CATEGORY_LABELS[cat] || cat}
                            </span>
                            <div className="kg-cat-bar-wrap">
                                <div
                                    className="kg-cat-bar"
                                    style={{
                                        width: `${(count / totalNodes) * 100}%`,
                                        background: CATEGORY_COLORS[cat] || '#6B7A8D',
                                    }}
                                />
                            </div>
                            <span className="kg-cat-count">{count}</span>
                        </div>
                    ))}
                </div>

                {/* Top entities */}
                <div className="kg-top-header">Top Entities</div>
                <div className="kg-top-list">
                    {topEntities.map((entity) => (
                        <div key={entity.id} className="kg-top-item">
                            <span
                                className="kg-cat-dot"
                                style={{ background: CATEGORY_COLORS[entity.category] || '#6B7A8D' }}
                            />
                            <span className="kg-top-name">{entity.label}</span>
                            <span className="kg-top-count">{entity.size} links</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
