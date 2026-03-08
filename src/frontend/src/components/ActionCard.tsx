import { useState } from 'react';

interface Action {
  id: string;
  action: string;
  title?: string;
  data_ref: string;
  pattern_id?: string;
  rationale: string;
  compound_summary: string;
}

interface Props {
  action: Action;
  index: number;
  expanded: boolean;
  onToggle: () => void;
}

function getToolBadge(patternId?: string, dataRef?: string): { icon: string; color: string; label: string } {
  const pid = patternId ?? '';
  if (pid.startsWith('p_burnout') || pid.startsWith('p_focus') || pid.startsWith('p_lead')) {
    return { icon: '◈', color: '#38BDF8', label: 'Calendar' };
  }
  if (pid.startsWith('p_undercharge') || pid.startsWith('p_rate')) {
    return { icon: '≋', color: '#ffffff', label: 'Notion' };
  }
  if (pid.startsWith('p_social') || pid.startsWith('p_portfolio')) {
    return { icon: 'Ω', color: '#7B61FF', label: 'Figma' };
  }
  // fallback: check data_ref prefix
  const dr = dataRef ?? '';
  if (dr.startsWith('calendar')) {
    return { icon: '◈', color: '#38BDF8', label: 'Calendar' };
  }
  if (dr.startsWith('notion') || dr.startsWith('lead')) {
    return { icon: '≋', color: '#ffffff', label: 'Notion' };
  }
  return { icon: 'λ', color: '#F59E0B', label: 'KG' };
}

export default function ActionCard({ action, index, expanded, onToggle }: Props) {
  const [hovered, setHovered] = useState(false);
  const badge = getToolBadge(action.pattern_id, action.data_ref);
  const qIndex = `Q${String(index + 1).padStart(2, '0')}`;

  return (
    <div
      onClick={onToggle}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? '#ffffff08' : 'transparent',
        border: '1px solid #2a2a3a',
        borderRadius: '8px',
        padding: '1rem',
        cursor: 'pointer',
        transition: 'background 0.15s ease',
        marginBottom: '0.5rem',
        userSelect: 'none',
      }}
    >
      {/* Main row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* Index */}
        <span
          style={{
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            color: '#555',
            minWidth: '2rem',
            flexShrink: 0,
          }}
        >
          {qIndex}
        </span>

        {/* Tool badge */}
        <span
          style={{
            fontFamily: 'monospace',
            fontSize: '1rem',
            color: badge.color,
            flexShrink: 0,
          }}
          title={badge.label}
        >
          {badge.icon}
        </span>

        {/* Action text */}
        <span
          style={{
            flex: 1,
            color: '#ffffff',
            fontSize: '0.95rem',
            lineHeight: 1.4,
          }}
        >
          {action.title ?? action.action}
        </span>

        {/* Right side: data_ref + chevron */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
          <span
            style={{
              fontFamily: 'monospace',
              fontSize: '0.7rem',
              color: '#444',
              background: '#1a1a2a',
              padding: '2px 6px',
              borderRadius: '4px',
              maxWidth: '120px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {action.data_ref}
          </span>
          <span
            style={{
              color: '#555',
              fontSize: '0.8rem',
              transition: 'transform 0.2s ease',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
              display: 'inline-block',
            }}
          >
            ▾
          </span>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div
          style={{
            marginTop: '0.75rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid #1e1e2e',
          }}
        >
          {/* Full action text if title was truncated */}
          {action.title && action.title !== action.action && (
            <p
              style={{
                color: '#aaa',
                fontSize: '0.85rem',
                marginBottom: '0.5rem',
                lineHeight: 1.5,
              }}
            >
              {action.action}
            </p>
          )}

          <div style={{ marginBottom: '0.5rem' }}>
            <span
              style={{
                fontSize: '0.65rem',
                color: '#555',
                letterSpacing: '0.08em',
                fontFamily: 'monospace',
                textTransform: 'uppercase',
                display: 'block',
                marginBottom: '0.25rem',
              }}
            >
              WHY
            </span>
            <p
              style={{
                color: '#888',
                fontSize: '0.85rem',
                lineHeight: 1.5,
                margin: 0,
              }}
            >
              {action.rationale}
            </p>
          </div>

          <div>
            <span
              style={{
                fontSize: '0.65rem',
                color: '#555',
                letterSpacing: '0.08em',
                fontFamily: 'monospace',
                textTransform: 'uppercase',
                display: 'block',
                marginBottom: '0.25rem',
              }}
            >
              COMPOUNDS TO
            </span>
            <p
              style={{
                color: '#888',
                fontSize: '0.85rem',
                lineHeight: 1.5,
                fontStyle: 'italic',
                margin: 0,
              }}
            >
              {action.compound_summary}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
