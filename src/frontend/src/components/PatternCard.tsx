import { useState } from 'react';

export interface Pattern {
  id: string;
  trend: 'upward' | 'downward' | 'stable' | 'cyclical';
  domains: string[];
  confidence: number;
  data_refs: string[];
  is_cross_domain: boolean;
  title: string;
  evidence_summary: string;
}

interface Props {
  pattern: Pattern;
  index: number;
}

const DOMAIN_COLORS: Record<string, string> = {
  financial: '#EF4444',
  calendar: '#38BDF8',
  lifelog: '#84CC16',
  health: '#84CC16',
  social: '#7B61FF',
};

const TREND_ICON: Record<string, { icon: string; color: string }> = {
  upward: { icon: '↗', color: '#22c55e' },
  downward: { icon: '↘', color: '#ef4444' },
  stable: { icon: '→', color: '#9ca3af' },
  cyclical: { icon: '↻', color: '#f59e0b' },
};

export default function PatternCard({ pattern, index }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [hovered, setHovered] = useState(false);

  const primaryDomain = pattern.domains[0] ?? 'financial';
  const primaryColor = DOMAIN_COLORS[primaryDomain] ?? '#7B61FF';
  const trend = TREND_ICON[pattern.trend] ?? TREND_ICON.stable;

  const firstSentence = pattern.evidence_summary.split('. ')[0] + (pattern.evidence_summary.includes('. ') ? '.' : '');

  const cardStyle: React.CSSProperties = {
    background: hovered ? '#16161f' : '#11111a',
    border: pattern.is_cross_domain
      ? `1px solid rgba(245,158,11,0.3)`
      : '1px solid rgba(255,255,255,0.07)',
    borderLeft: pattern.is_cross_domain ? '4px solid #F59E0B' : '1px solid rgba(255,255,255,0.07)',
    borderRadius: '12px',
    padding: pattern.is_cross_domain ? '20px 20px 20px 16px' : '16px',
    cursor: 'pointer',
    position: 'relative',
    transition: 'background 0.2s, box-shadow 0.2s',
    boxShadow: hovered && pattern.is_cross_domain
      ? '0 0 16px rgba(245,158,11,0.15)'
      : hovered
      ? '0 4px 16px rgba(0,0,0,0.3)'
      : 'none',
    animationDelay: `${index * 150}ms`,
    animation: 'fadeInUp 0.4s ease both',
  };

  return (
    <div
      style={cardStyle}
      onClick={() => setExpanded(!expanded)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Cross-domain badge */}
      {pattern.is_cross_domain && (
        <div style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          background: 'rgba(245,158,11,0.15)',
          border: '1px solid rgba(245,158,11,0.4)',
          color: '#F59E0B',
          fontSize: '10px',
          fontWeight: 700,
          letterSpacing: '0.08em',
          padding: '2px 8px',
          borderRadius: '4px',
          textTransform: 'uppercase',
        }}>
          Cross-Domain Insight
        </div>
      )}

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '10px', paddingRight: pattern.is_cross_domain ? '140px' : '24px' }}>
        {/* Trend icon */}
        <span style={{ fontSize: '18px', color: trend.color, lineHeight: 1, marginTop: '1px', flexShrink: 0 }}>
          {trend.icon}
        </span>
        {/* Title */}
        <span style={{ fontWeight: 700, color: '#fff', fontSize: '15px', lineHeight: 1.3 }}>
          {pattern.title}
        </span>
        {/* Expand chevron */}
        <span style={{
          marginLeft: 'auto',
          color: '#555',
          fontSize: '14px',
          transform: expanded ? 'rotate(90deg)' : 'none',
          transition: 'transform 0.2s',
          flexShrink: 0,
        }}>
          ›
        </span>
      </div>

      {/* Domain badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
        {pattern.domains.map((d) => (
          <span key={d} style={{
            background: `${DOMAIN_COLORS[d] ?? '#7B61FF'}22`,
            border: `1px solid ${DOMAIN_COLORS[d] ?? '#7B61FF'}55`,
            color: DOMAIN_COLORS[d] ?? '#7B61FF',
            fontSize: '11px',
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: '20px',
            textTransform: 'capitalize',
          }}>
            {d}
          </span>
        ))}
      </div>

      {/* Confidence bar */}
      <div style={{ marginBottom: '10px' }}>
        <div style={{ height: '3px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${Math.round(pattern.confidence * 100)}%`,
            background: primaryColor,
            borderRadius: '2px',
            transition: 'width 0.6s ease',
          }} />
        </div>
        <div style={{ fontSize: '11px', color: '#555', marginTop: '4px' }}>
          {Math.round(pattern.confidence * 100)}% confidence
        </div>
      </div>

      {/* Evidence preview */}
      <div style={{ fontSize: '13px', color: '#888', lineHeight: 1.5 }}>
        {expanded ? pattern.evidence_summary : firstSentence}
      </div>

      {/* Expanded: data_refs */}
      {expanded && pattern.data_refs.length > 0 && (
        <div style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {pattern.data_refs.map((ref) => (
            <span key={ref} style={{
              fontFamily: 'monospace',
              fontSize: '11px',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#aaa',
              padding: '2px 8px',
              borderRadius: '4px',
            }}>
              [{ref}]
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
