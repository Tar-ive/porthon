import { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import Graph from 'graphology';
import { SigmaContainer, useRegisterEvents, useSigma } from '@react-sigma/core';
import '@react-sigma/core/lib/style.css';

interface KGNode {
    id: string;
    label: string;
    category: string;
    size: number;
}

interface KGEdge {
    id: string;
    source: string;
    target: string;
}

interface KGData {
    nodes: KGNode[];
    edges: KGEdge[];
    meta: { total_nodes: number; total_edges: number };
}

const CATEGORY_COLORS: Record<string, string> = {
    person: '#c8922a',
    tool: '#38BDF8',
    place: '#84CC16',
    financial: '#EF4444',
    concept: '#7B61FF',
};
const DEFAULT_COLOR = '#6B7A8D';

const DEMO_TOKEN = 'Bearer sk_demo_default';

// Custom label renderer: no white background, text matches node color
function drawLabel(
    context: CanvasRenderingContext2D,
    data: {
        label: string;
        x: number;
        y: number;
        size: number;
        color: string;
    },
    settings: { labelSize: number; labelFont: string; labelWeight: string }
) {
    if (!data.label) return;

    const size = settings.labelSize || 10;
    const font = settings.labelFont || 'IBM Plex Mono';
    const weight = settings.labelWeight || '500';

    context.font = `${weight} ${size}px ${font}`;
    context.fillStyle = data.color || '#e8dfc8';
    context.textBaseline = 'middle';
    context.fillText(data.label, data.x + data.size + 4, data.y);
}

// ── Agent definitions with SVG paths ──────────────────────────────
const AGENTS = [
    {
        id: 'kg_worker',
        label: 'KG Search',
        color: '#c8922a',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <path d="M21 21l-4.35-4.35" />
            </svg>
        ),
        targetCategories: ['concept', 'person'],
    },
    {
        id: 'calendar_worker',
        label: 'Calendar',
        color: '#38BDF8',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
        ),
        targetCategories: ['place'],
    },
    {
        id: 'notion_leads_worker',
        label: 'Notion',
        color: '#FFFFFF',
        icon: (
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L2.84 2.298c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.84-.046.933-.56.933-1.167V6.354c0-.606-.233-.933-.746-.886l-15.177.886c-.56.047-.747.327-.747.934zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.747 0-.933-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.513.28-.886.747-.932zM1.936 1.035l13.31-.98c1.634-.14 2.054-.047 3.082.7l4.249 2.986c.7.513.933.653.933 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.046-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.84.373-1.54 1.448-1.632z" />
            </svg>
        ),
        targetCategories: ['tool'],
    },
    {
        id: 'facebook_worker',
        label: 'Facebook',
        color: '#1877F2',
        icon: (
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
            </svg>
        ),
        targetCategories: ['concept'],
    },
    {
        id: 'figma_worker',
        label: 'Figma',
        color: '#A259FF',
        icon: (
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M15.852 8.981h-4.588V0h4.588c2.476 0 4.49 2.014 4.49 4.49s-2.014 4.491-4.49 4.491zM12.735 7.51h3.117c1.665 0 3.019-1.355 3.019-3.019s-1.354-3.019-3.019-3.019h-3.117V7.51zm0 8.962h-4.588c-2.476 0-4.49-2.014-4.49-4.49s2.014-4.49 4.49-4.49h4.588v8.98zM4.147 12c0 1.665 1.354 3.019 3.019 3.019h3.117V8.981H7.166C5.501 8.981 4.147 10.335 4.147 12zm0 8.981c0 2.694 2.192 4.872 4.872 4.872 2.694 0 4.907-2.192 4.907-4.872v-4.588H9.019c-2.694 0-4.872 2.178-4.872 4.588zm15.116-13.471c0 2.476-2.014 4.49-4.49 4.49h-4.588V3.019h4.588c2.476 0 4.49 2.014 4.49 4.491z" />
            </svg>
        ),
        targetCategories: ['tool'],
    },
    {
        id: 'notion_opportunity_worker',
        label: 'Opps Tracker',
        color: '#84CC16',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
            </svg>
        ),
        targetCategories: ['financial'],
    },
];

// GraphEvents — hover highlighting
function GraphEvents() {
    const sigma = useSigma();
    const registerEvents = useRegisterEvents();
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);

    useEffect(() => {
        registerEvents({
            enterNode: (event: { node: string }) => setHoveredNode(event.node),
            leaveNode: () => setHoveredNode(null),
        });
    }, [registerEvents]);

    useEffect(() => {
        const graph = sigma.getGraph();

        sigma.setSetting(
            'nodeReducer',
            (node: string, data: Record<string, unknown>) => {
                const res = { ...data };
                if (hoveredNode) {
                    if (node === hoveredNode) {
                        res['highlighted'] = true;
                        res['zIndex'] = 1;
                    } else if (
                        graph.hasEdge(hoveredNode, node) ||
                        graph.hasEdge(node, hoveredNode)
                    ) {
                        res['highlighted'] = true;
                    } else {
                        res['color'] = '#1e222c';
                        res['label'] = '';
                    }
                }
                return res;
            }
        );

        sigma.setSetting(
            'edgeReducer',
            (edge: string, data: Record<string, unknown>) => {
                const res = { ...data };
                if (hoveredNode) {
                    const ends = graph.extremities(edge);
                    if (!ends.includes(hoveredNode)) {
                        res['hidden'] = true;
                    } else {
                        res['color'] = '#c8922a';
                        res['size'] = 2;
                    }
                }
                return res;
            }
        );

        return () => {
            sigma.setSetting('nodeReducer', null);
            sigma.setSetting('edgeReducer', null);
        };
    }, [hoveredNode, sigma]);

    return null;
}

// ── Agent animation overlay ────────────────────────────────────────
function AgentOverlay({
    sigmaRef,
    kgNodes,
}: {
    sigmaRef: React.RefObject<any>;
    kgNodes: KGNode[];
}) {
    const [agentPositions, setAgentPositions] = useState<
        Record<string, { x: number; y: number; targetLabel: string }>
    >({});
    const [trails, setTrails] = useState<
        { id: string; x: number; y: number; color: string }[]
    >([]);
    const [pulses, setPulses] = useState<
        { id: string; x: number; y: number; color: string }[]
    >([]);

    const getNodeScreenPos = useCallback(
        (nodeId: string) => {
            const sigma = sigmaRef.current;
            if (!sigma) return null;
            const graph = sigma.getGraph();
            if (!graph.hasNode(nodeId)) return null;
            const pos = sigma.getNodeDisplayData(nodeId);
            if (!pos) return null;
            return { x: pos.x, y: pos.y };
        },
        [sigmaRef]
    );

    const categoryNodes = useMemo(() => {
        const map: Record<string, string[]> = {};
        for (const n of kgNodes) {
            if (!map[n.category]) map[n.category] = [];
            map[n.category].push(n.id);
        }
        return map;
    }, [kgNodes]);

    useEffect(() => {
        let running = true;
        const trailId = { current: 0 };
        let intervalId: ReturnType<typeof setInterval>;

        const moveAgents = () => {
            if (!running) return;
            const sigma = sigmaRef.current;
            if (!sigma) {
                setTimeout(moveAgents, 500);
                return;
            }

            const newPositions: Record<
                string,
                { x: number; y: number; targetLabel: string }
            > = {};
            const newTrails: { id: string; x: number; y: number; color: string }[] =
                [];
            const newPulses: { id: string; x: number; y: number; color: string }[] =
                [];

            for (const agent of AGENTS) {
                const candidates = agent.targetCategories.flatMap(
                    (cat) => categoryNodes[cat] || []
                );
                if (candidates.length === 0) continue;
                const targetNodeId =
                    candidates[Math.floor(Math.random() * candidates.length)];
                const pos = getNodeScreenPos(targetNodeId);
                if (!pos) continue;
                const targetNode = kgNodes.find((n) => n.id === targetNodeId);

                newPositions[agent.id] = {
                    x: pos.x,
                    y: pos.y,
                    targetLabel: targetNode?.label || '',
                };

                newTrails.push({
                    id: `trail-${trailId.current++}`,
                    x: pos.x,
                    y: pos.y,
                    color: agent.color,
                });

                newPulses.push({
                    id: `pulse-${trailId.current++}`,
                    x: pos.x,
                    y: pos.y,
                    color: agent.color,
                });
            }

            setAgentPositions(newPositions);
            setTrails((prev) => [...prev, ...newTrails].slice(-20));
            setPulses(newPulses);
        };

        const startDelay = setTimeout(() => {
            moveAgents();
            intervalId = setInterval(moveAgents, 4000);
        }, 2000);

        return () => {
            running = false;
            clearTimeout(startDelay);
            clearInterval(intervalId);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sigmaRef, kgNodes, categoryNodes, getNodeScreenPos]);

    return (
        <div className="agent-overlay">
            {trails.map((t) => (
                <div
                    key={t.id}
                    className="agent-trail"
                    style={{
                        left: t.x - 16,
                        top: t.y - 16,
                        background: t.color,
                    }}
                />
            ))}
            {pulses.map((p) => (
                <div
                    key={p.id}
                    className="node-pulse"
                    style={{
                        left: p.x - 8,
                        top: p.y - 8,
                        width: 16,
                        height: 16,
                        background: p.color,
                    }}
                />
            ))}
            {AGENTS.map((agent) => {
                const pos = agentPositions[agent.id];
                if (!pos) return null;
                return (
                    <div
                        key={agent.id}
                        className="agent-icon"
                        style={{
                            left: pos.x - 16,
                            top: pos.y - 16,
                            borderColor: agent.color,
                            color: agent.color,
                        }}
                        title={`${agent.label} → ${pos.targetLabel}`}
                    >
                        {agent.icon}
                    </div>
                );
            })}
        </div>
    );
}

// ── Main component ─────────────────────────────────────────────────
export default function AnimatedKnowledgeGraph() {
    const [data, setData] = useState<KGData | null>(null);
    const [phase, setPhase] = useState<'loading' | 'ready' | 'error'>('loading');
    const sigmaRef = useRef<any>(null);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch('/v1/knowledge-graph', {
                    headers: { Authorization: DEMO_TOKEN },
                });
                const body = await res.json();
                setData(body);
                setPhase('ready');
            } catch {
                setPhase('error');
            }
        })();
    }, []);

    const graph = useMemo(() => {
        if (!data) return null;
        const g = new Graph({ multi: false, type: 'undirected' });

        // ── Circular layout: arrange nodes in a circle by category ──
        // Group nodes by category, then lay them out in circular arcs
        const categories = ['person', 'tool', 'place', 'financial', 'concept'];
        const grouped: Record<string, KGNode[]> = {};
        for (const cat of categories) grouped[cat] = [];
        for (const node of data.nodes) {
            const cat = categories.includes(node.category) ? node.category : 'concept';
            grouped[cat].push(node);
        }

        // Flatten in category order for sector-based circular layout
        const ordered: KGNode[] = [];
        for (const cat of categories) {
            // Sort within category by connection count (larger = first)
            grouped[cat].sort((a, b) => b.size - a.size);
            ordered.push(...grouped[cat]);
        }

        const total = ordered.length;
        const radius = 45; // graph coordinate space radius

        ordered.forEach((node, i) => {
            const angle = (2 * Math.PI * i) / total - Math.PI / 2;
            // Add some radial jitter based on connection count for visual interest
            const r = radius + (node.size > 5 ? -8 : node.size > 2 ? -3 : 5);
            g.addNode(node.id, {
                label: node.label,
                size: Math.max(3, Math.min(20, Math.sqrt(node.size) * 2.5)),
                color: CATEGORY_COLORS[node.category] || DEFAULT_COLOR,
                x: Math.cos(angle) * r + 50,
                y: Math.sin(angle) * r + 50,
            });
        });

        const nodeSet = new Set(data.nodes.map((n) => n.id));
        for (const edge of data.edges) {
            if (
                nodeSet.has(edge.source) &&
                nodeSet.has(edge.target) &&
                edge.source !== edge.target
            ) {
                try {
                    g.addEdge(edge.source, edge.target, {
                        size: 0.3,
                        color: 'rgba(200, 146, 42, 0.06)',
                    });
                } catch {
                    // skip duplicate edges
                }
            }
        }

        return g;
    }, [data]);

    const handleZoomIn = useCallback(() => {
        const camera = sigmaRef.current?.getCamera();
        if (camera) camera.animatedZoom({ duration: 300 });
    }, []);

    const handleZoomOut = useCallback(() => {
        const camera = sigmaRef.current?.getCamera();
        if (camera) camera.animatedUnzoom({ duration: 300 });
    }, []);

    const handleReset = useCallback(() => {
        const camera = sigmaRef.current?.getCamera();
        if (camera) camera.animatedReset({ duration: 300 });
    }, []);

    return (
        <div className="ops-panel kg-panel">
            <div className="ops-panel-header">
                <span className="ops-panel-title">Knowledge Graph</span>
                {data && (
                    <>
                        <span className="ops-panel-badge">
                            {data.meta.total_nodes} nodes
                        </span>
                        <span className="ops-panel-badge">
                            {data.meta.total_edges} edges
                        </span>
                    </>
                )}
            </div>
            <div className="kg-container">
                {phase === 'loading' && (
                    <div className="kg-loading">
                        <span className="kg-loading-text">Loading knowledge graph…</span>
                    </div>
                )}
                {phase === 'error' && (
                    <div className="kg-loading">
                        <span className="kg-loading-text" style={{ color: '#fca5a5' }}>
                            Failed to load graph
                        </span>
                    </div>
                )}
                {phase === 'ready' && graph && (
                    <>
                        <SigmaContainer
                            graph={graph}
                            ref={sigmaRef}
                            style={{ width: '100%', height: '100%' }}
                            settings={{
                                renderLabels: true,
                                labelSize: 10,
                                labelColor: { attribute: 'color' },
                                labelFont: 'IBM Plex Mono',
                                labelWeight: '500',
                                defaultDrawNodeLabel: drawLabel as any,
                                defaultEdgeColor: 'rgba(200, 146, 42, 0.06)',
                                defaultNodeColor: DEFAULT_COLOR,
                                labelDensity: 0.5,
                                labelGridCellSize: 100,
                                labelRenderedSizeThreshold: 6,
                                zIndex: true,
                            }}
                        >
                            <GraphEvents />
                        </SigmaContainer>
                        {data && (
                            <AgentOverlay sigmaRef={sigmaRef} kgNodes={data.nodes} />
                        )}
                        <div className="kg-controls">
                            <button
                                className="kg-control-btn"
                                onClick={handleZoomIn}
                                title="Zoom In"
                            >
                                +
                            </button>
                            <button
                                className="kg-control-btn"
                                onClick={handleZoomOut}
                                title="Zoom Out"
                            >
                                −
                            </button>
                            <button
                                className="kg-control-btn"
                                onClick={handleReset}
                                title="Reset"
                            >
                                ⟲
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
