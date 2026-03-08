import { useEffect, useState, useRef } from 'react';
import Graph from 'graphology';
import { SigmaContainer, useRegisterEvents, useSigma } from '@react-sigma/core';
import '@react-sigma/core/lib/style.css';

interface Props {
  onContinue: () => void;
}

// ── KG types ────────────────────────────────────────────────────────
interface KGNode { id: string; label: string; category: string; size: number; }
interface KGEdge { id: string; source: string; target: string; }

const CATEGORY_COLORS: Record<string, string> = {
  person: '#c8922a',
  tool: '#38BDF8',
  place: '#84CC16',
  financial: '#EF4444',
  concept: '#7B61FF',
};
const DEFAULT_COLOR = '#6B7A8D';
const DEMO_TOKEN = 'Bearer sk_demo_default';

// Same label renderer as AnimatedKnowledgeGraph
function drawLabel(
  context: CanvasRenderingContext2D,
  data: { label: string; x: number; y: number; size: number; color: string },
  settings: { labelSize: number; labelFont: string; labelWeight: string }
) {
  if (!data.label) return;
  const size = settings.labelSize || 10;
  context.font = `${settings.labelWeight || '500'} ${size}px ${settings.labelFont || 'IBM Plex Mono'}`;
  context.fillStyle = data.color || '#e8dfc8';
  context.textBaseline = 'middle';
  context.fillText(data.label, data.x + data.size + 4, data.y);
}

// Pre-compute circular layout positions for all nodes
function computeLayout(nodes: KGNode[]): Map<string, { x: number; y: number; color: string; size: number; label: string }> {
  const categories = ['person', 'tool', 'place', 'financial', 'concept'];
  const grouped: Record<string, KGNode[]> = {};
  for (const cat of categories) grouped[cat] = [];
  for (const node of nodes) {
    const cat = categories.includes(node.category) ? node.category : 'concept';
    grouped[cat].push(node);
  }
  const ordered: KGNode[] = [];
  for (const cat of categories) {
    grouped[cat].sort((a, b) => b.size - a.size);
    ordered.push(...grouped[cat]);
  }
  const total = ordered.length;
  const radius = 45;
  const result = new Map<string, { x: number; y: number; color: string; size: number; label: string }>();
  ordered.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / total - Math.PI / 2;
    const r = radius + (node.size > 5 ? -8 : node.size > 2 ? -3 : 5);
    result.set(node.id, {
      label: node.label,
      size: Math.max(3, Math.min(20, Math.sqrt(node.size) * 2.5)),
      color: CATEGORY_COLORS[node.category] || DEFAULT_COLOR,
      x: Math.cos(angle) * r + 50,
      y: Math.sin(angle) * r + 50,
    });
  });
  return result;
}

// ── Hover + click interaction ─────────────────────────────────────
function GraphEvents() {
  const sigma = useSigma();
  const registerEvents = useRegisterEvents();
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [lockedNode, setLockedNode] = useState<string | null>(null);

  useEffect(() => {
    registerEvents({
      enterNode: (event: { node: string }) => {
        if (!lockedNode) setHoveredNode(event.node);
      },
      leaveNode: () => {
        if (!lockedNode) setHoveredNode(null);
      },
      clickNode: (event: { node: string }) => {
        setLockedNode(prev => prev === event.node ? null : event.node);
        setHoveredNode(null);
      },
      clickStage: () => {
        setLockedNode(null);
        setHoveredNode(null);
      },
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [registerEvents, lockedNode]);

  useEffect(() => {
    const graph = sigma.getGraph();
    const focusNode = lockedNode ?? hoveredNode;

    sigma.setSetting('nodeReducer', (node: string, data: Record<string, unknown>) => {
      const res = { ...data };
      if (focusNode) {
        if (node === focusNode) {
          res['highlighted'] = true;
          res['zIndex'] = 1;
        } else if (graph.hasEdge(focusNode, node) || graph.hasEdge(node, focusNode)) {
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
      if (focusNode) {
        const ends = graph.extremities(edge);
        if (!ends.includes(focusNode)) {
          res['hidden'] = true;
        } else {
          res['color'] = 'rgba(200, 146, 42, 0.5)';
          res['size'] = 1.5;
        }
      }
      return res;
    });

    return () => {
      sigma.setSetting('nodeReducer', null);
      sigma.setSetting('edgeReducer', null);
    };
  }, [hoveredNode, lockedNode, sigma]);

  return null;
}

// ── Live-building Knowledge Graph ────────────────────────────────────
function BuildingKnowledgeGraph() {
  // Stable graph instance — Sigma subscribes to its mutation events
  const graph = useRef<Graph>(new Graph({ multi: false, type: 'undirected' })).current;
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const timers: ReturnType<typeof setTimeout>[] = [];

    fetch('/v1/knowledge-graph', { headers: { Authorization: DEMO_TOKEN } })
      .then(r => r.json())
      .then((data: { nodes: KGNode[]; edges: KGEdge[] }) => {
        if (cancelled) return;

        const layout = computeLayout(data.nodes);

        // Deduplicate + validate edges upfront
        const nodeSet = new Set(data.nodes.map(n => n.id));
        const seen = new Set<string>();
        const edges = data.edges.filter(e => {
          if (!nodeSet.has(e.source) || !nodeSet.has(e.target) || e.source === e.target) return false;
          const key = [e.source, e.target].sort().join('|');
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });

        // Fit everything into ~11s:
        // nodes over 0–7.5s, edges over 7.5–10.5s
        const nodeInterval = Math.max(30, 7500 / data.nodes.length);
        const edgesStart = data.nodes.length * nodeInterval + 300;
        const edgeInterval = edges.length > 0 ? Math.max(10, 3000 / edges.length) : 20;

        setReady(true);

        // Add nodes one by one
        data.nodes.forEach((node, i) => {
          timers.push(
            setTimeout(() => {
              if (cancelled) return;
              const pos = layout.get(node.id);
              if (pos && !graph.hasNode(node.id)) {
                graph.addNode(node.id, pos);
              }
            }, i * nodeInterval)
          );
        });

        // Add edges one by one after nodes are placed
        edges.forEach((edge, i) => {
          timers.push(
            setTimeout(() => {
              if (cancelled) return;
              if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
                try {
                  graph.addEdge(edge.source, edge.target, {
                    size: 0.3,
                    color: 'rgba(200, 146, 42, 0.08)',
                  });
                } catch { /* skip duplicate */ }
              }
            }, edgesStart + i * edgeInterval)
          );
        });
      })
      .catch(() => {
        if (!cancelled) setReady(true); // show empty canvas on error
      });

    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
    };
  // graph is stable (from ref), no deps needed
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!ready) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#333' }}>
        <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '0.7rem', letterSpacing: '0.1em' }}>
          Connecting…
        </span>
      </div>
    );
  }

  return (
    <SigmaContainer
      graph={graph}
      style={{ width: '100%', height: '100%', background: 'transparent' }}
      settings={{
        renderLabels: true,
        labelSize: 10,
        labelColor: { attribute: 'color' },
        labelFont: 'IBM Plex Mono',
        labelWeight: '500',
        defaultDrawNodeLabel: drawLabel as any,
        defaultEdgeColor: 'rgba(200, 146, 42, 0.08)',
        defaultNodeColor: DEFAULT_COLOR,
        labelDensity: 0.4,
        labelGridCellSize: 100,
        labelRenderedSizeThreshold: 6,
        zIndex: true,
      }}
    >
      <GraphEvents />
    </SigmaContainer>
  );
}

// ── Data source list ─────────────────────────────────────────────────
const DATA_SOURCES = [
  { label: 'Financial data', value: '2,800 transactions ingested' },
  { label: 'Calendar events', value: '1,200 events mapped' },
  { label: 'Health logs', value: '365 days of activity' },
  { label: 'Social activity', value: '340 posts analyzed' },
  { label: 'Knowledge graph', value: 'Entities linked, relationships extracted' },
];

const REVEAL_DELAYS = [1500, 3000, 4500, 6000, 7500];

// ── IngestScreen ─────────────────────────────────────────────────────
export default function IngestScreen({ onContinue }: Props) {
  const [revealed, setRevealed] = useState<boolean[]>([false, false, false, false, false]);
  const [showProgress, setShowProgress] = useState(false);
  const [progressWidth, setProgressWidth] = useState(0);
  const [showButton, setShowButton] = useState(false);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];

    REVEAL_DELAYS.forEach((delay, i) => {
      timers.push(
        setTimeout(() => {
          setRevealed(r => r.map((v, idx) => (idx === i ? true : v)));
        }, delay)
      );
    });

    timers.push(
      setTimeout(() => {
        setShowProgress(true);
        requestAnimationFrame(() => {
          requestAnimationFrame(() => setProgressWidth(100));
        });
      }, 9000)
    );

    timers.push(setTimeout(() => setShowButton(true), 10000));

    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <>
      <style>{`
        @keyframes ingest-pulse {
          0%   { transform: scale(1.5); opacity: 0.4; }
          60%  { transform: scale(1.1); opacity: 1; }
          100% { transform: scale(1);   opacity: 1; }
        }
        .ingest-continue-btn {
          padding: 0.4rem 1.2rem;
          background: var(--amber, #c8922a);
          color: #0a0807;
          border: none;
          border-radius: 999px;
          cursor: pointer;
          font-size: 0.6rem;
          font-weight: 500;
          font-family: 'IBM Plex Mono', monospace;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          transition: background 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
        }
        .ingest-continue-btn:hover {
          background: #d9a03d;
          box-shadow: 0 0 16px rgba(200, 146, 42, 0.4);
          transform: translateY(-1px);
        }
      `}</style>

      <div style={{ display: 'flex', height: '100vh', width: '100vw', background: '#0a0a0f', overflow: 'hidden' }}>

        {/* ── Left: live-building Knowledge Graph ── */}
        <div style={{ flex: '0 0 55%', position: 'relative', height: '100%' }}>
          <BuildingKnowledgeGraph />
        </div>

        {/* ── Right: content column ── */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '3rem 3.5rem',
          gap: '1.5rem',
          borderLeft: '1px solid rgba(255,255,255,0.06)',
        }}>
          {/* Label */}
          <p style={{
            margin: 0,
            fontSize: '0.7rem',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            color: '#4a5568',
            fontFamily: 'IBM Plex Mono, monospace',
          }}>
            Questline · Theo Nakamura
          </p>

          {/* Headline */}
          <h1 style={{
            margin: 0,
            fontSize: '2.4rem',
            fontWeight: 700,
            color: '#f0ece4',
            lineHeight: 1.15,
            letterSpacing: '-0.02em',
          }}>
            Building your<br />knowledge graph
          </h1>

          {/* Subtext */}
          <p style={{
            margin: 0,
            fontSize: '0.95rem',
            color: '#6b7280',
            lineHeight: 1.6,
            maxWidth: '32ch',
          }}>
            Connecting patterns across financial, calendar, health, and social data
          </p>

          {/* Data source list */}
          <ul style={{
            listStyle: 'none',
            margin: '0.5rem 0 0',
            padding: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
          }}>
            {DATA_SOURCES.map((source, i) => (
              <li
                key={source.label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  opacity: revealed[i] ? 1 : 0,
                  transform: revealed[i] ? 'translateY(0)' : 'translateY(8px)',
                  transition: 'opacity 0.5s ease, transform 0.5s ease',
                }}
              >
                <span style={{
                  fontSize: '1rem',
                  color: revealed[i] ? '#4ade80' : '#c8922a',
                  transition: 'color 0.3s ease',
                  minWidth: '1.2rem',
                  textAlign: 'center',
                  animation: revealed[i] ? 'ingest-pulse 0.6s ease-out' : 'none',
                }}>
                  {revealed[i] ? '✓' : '◈'}
                </span>
                <span style={{ display: 'flex', gap: '0.6rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
                  <span style={{
                    fontSize: '0.9rem',
                    fontWeight: 600,
                    color: '#e2ddd6',
                    fontFamily: 'IBM Plex Mono, monospace',
                  }}>
                    {source.label}
                  </span>
                  <span style={{
                    fontSize: '0.8rem',
                    color: '#4a5568',
                    fontFamily: 'IBM Plex Mono, monospace',
                  }}>
                    {source.value}
                  </span>
                </span>
              </li>
            ))}
          </ul>

          {/* Progress bar */}
          {showProgress && (
            <div style={{
              marginTop: '0.5rem',
              height: '2px',
              background: 'rgba(255,255,255,0.08)',
              borderRadius: '2px',
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${progressWidth}%`,
                background: 'linear-gradient(90deg, #c8922a, #e8dfc8)',
                borderRadius: '2px',
                transition: 'width 1s ease',
              }} />
            </div>
          )}

          {/* Continue button */}
          <div style={{
            marginTop: '0.5rem',
            opacity: showButton ? 1 : 0,
            transform: showButton ? 'translateY(0)' : 'translateY(6px)',
            transition: 'opacity 0.5s ease, transform 0.5s ease',
          }}>
            <button onClick={onContinue} className="ingest-continue-btn">
              Continue →
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
