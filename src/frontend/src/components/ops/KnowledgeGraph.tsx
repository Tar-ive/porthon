import { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import Graph from 'graphology';
import { SigmaContainer, useRegisterEvents, useSigma } from '@react-sigma/core';
import { useLayoutForceAtlas2 } from '@react-sigma/layout-forceatlas2';
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
    person: '#c8922a',    // amber
    tool: '#38BDF8',      // ice blue
    place: '#84CC16',     // green
    financial: '#EF4444', // red
    concept: '#7B61FF',   // violet
};
const DEFAULT_COLOR = '#6B7A8D';

const DEMO_TOKEN = 'Bearer sk_demo_default';

// Inner component that has access to Sigma context
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

    // Update node/edge rendering based on hover
    useEffect(() => {
        const graph = sigma.getGraph();

        sigma.setSetting('nodeReducer', (node: string, data: Record<string, unknown>) => {
            const res = { ...data };
            if (hoveredNode) {
                if (node === hoveredNode) {
                    res['highlighted'] = true;
                    res['zIndex'] = 1;
                } else if (graph.hasEdge(hoveredNode, node) || graph.hasEdge(node, hoveredNode)) {
                    res['highlighted'] = true;
                } else {
                    res['color'] = '#1e222c';
                    res['label'] = '';
                }
            }
            return res;
        });

        sigma.setSetting('edgeReducer', (edge: string, data: Record<string, unknown>) => {
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
        });

        return () => {
            sigma.setSetting('nodeReducer', null);
            sigma.setSetting('edgeReducer', null);
        };
    }, [hoveredNode, sigma]);

    return null;
}

function GraphLayout() {
    const { assign } = useLayoutForceAtlas2({
        iterations: 100,
        settings: {
            gravity: 1,
            scalingRatio: 4,
            barnesHutOptimize: true,
            slowDown: 5,
        },
    });

    useEffect(() => {
        assign();
    }, [assign]);

    return null;
}

export default function KnowledgeGraph() {
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

        for (const node of data.nodes) {
            // Random initial position
            g.addNode(node.id, {
                label: node.label,
                size: Math.max(3, Math.min(20, Math.sqrt(node.size) * 2.5)),
                color: CATEGORY_COLORS[node.category] || DEFAULT_COLOR,
                x: Math.random() * 100,
                y: Math.random() * 100,
            });
        }

        const nodeSet = new Set(data.nodes.map((n) => n.id));
        for (const edge of data.edges) {
            if (nodeSet.has(edge.source) && nodeSet.has(edge.target) && edge.source !== edge.target) {
                try {
                    g.addEdge(edge.source, edge.target, {
                        size: 0.5,
                        color: 'rgba(200, 146, 42, 0.12)',
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
                        <span className="ops-panel-badge">{data.meta.total_nodes} nodes</span>
                        <span className="ops-panel-badge">{data.meta.total_edges} edges</span>
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
                                labelColor: { color: '#e8dfc8' },
                                labelFont: 'IBM Plex Mono',
                                defaultEdgeColor: 'rgba(200, 146, 42, 0.12)',
                                defaultNodeColor: DEFAULT_COLOR,
                                labelDensity: 0.5,
                                labelGridCellSize: 100,
                                labelRenderedSizeThreshold: 8,
                                zIndex: true,
                            }}
                        >
                            <GraphEvents />
                            <GraphLayout />
                        </SigmaContainer>
                        <div className="kg-controls">
                            <button className="kg-control-btn" onClick={handleZoomIn} title="Zoom In">+</button>
                            <button className="kg-control-btn" onClick={handleZoomOut} title="Zoom Out">−</button>
                            <button className="kg-control-btn" onClick={handleReset} title="Reset">⟲</button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
