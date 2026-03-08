import { useEffect, useState } from 'react';
import PatternCard from '../components/PatternCard';
import type { Pattern } from '../components/PatternCard';
import { useAgentStream } from '../hooks/useAgentStream';

interface Props {
  onContinue: () => void;
}

const FALLBACK_PATTERNS: Pattern[] = [
  {
    id: 'p_burnout',
    is_cross_domain: true,
    title: 'Burnout Cascade',
    domains: ['financial', 'calendar', 'lifelog'],
    confidence: 0.87,
    trend: 'cyclical',
    data_refs: ['calendar_2026-02-10'],
    evidence_summary:
      'After weeks with 30+ hours of meetings, exercise drops and delivery food spending triples. Breaking this cycle is the highest-leverage intervention.',
  },
  {
    id: 'p_undercharge',
    is_cross_domain: false,
    title: 'Chronic Undercharging',
    domains: ['financial'],
    confidence: 0.91,
    trend: 'stable',
    data_refs: ['transactions_2026-01-15'],
    evidence_summary:
      '7 of the last 9 invoices were below rate floor. Average billed at $640 against a $1,200 target.',
  },
  {
    id: 'p_focus',
    is_cross_domain: true,
    title: 'Location-Dependent Focus',
    domains: ['calendar', 'lifelog'],
    confidence: 0.79,
    trend: 'stable',
    data_refs: ['calendar_2026-01-21'],
    evidence_summary:
      'Theo completes 3x more deep work on days at the UT library vs. home. Tuesday and Thursday afternoons show highest focus scores.',
  },
];

const skeletonStyle: React.CSSProperties = {
  background: 'linear-gradient(90deg, #16161f 25%, #1e1e2e 50%, #16161f 75%)',
  backgroundSize: '200% 100%',
  animation: 'shimmer 1.5s infinite',
  borderRadius: '12px',
  height: '120px',
  border: '1px solid rgba(255,255,255,0.06)',
};

export default function PatternsScreen({ onContinue }: Props) {
  const [patterns, setPatterns] = useState<Pattern[] | null>(null);
  const { isAnalyzing, changedDomain } = useAgentStream();

  useEffect(() => {
    fetch('/api/patterns?persona_id=p05', {
      headers: { Authorization: 'Bearer sk_demo_default' },
    })
      .then((r) => r.json())
      .then((data) => setPatterns(data.data && data.data.length > 0 ? data.data : FALLBACK_PATTERNS))
      .catch(() => setPatterns(FALLBACK_PATTERNS));
  }, []);

  const crossDomain = patterns?.filter((p) => p.is_cross_domain) ?? [];
  const singleDomain = patterns?.filter((p) => !p.is_cross_domain) ?? [];

  return (
    <>
      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        .patterns-continue-btn:hover {
          background: #d9a03d !important;
          box-shadow: 0 0 16px rgba(200, 146, 42, 0.4);
          transform: translateY(-1px);
        }
        @keyframes amberPulse {
          0%, 100% { box-shadow: 0 0 0 2px #F59E0B66; }
          50% { box-shadow: 0 0 0 4px #F59E0B33; }
        }
      `}</style>

      <div style={{
        minHeight: '100vh',
        background: '#0a0a0f',
        color: '#fff',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}>
        {/* Sticky header */}
        <div style={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          background: 'rgba(10,10,15,0.92)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          padding: '12px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span style={{ color: '#555', fontSize: '12px', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Pattern Analysis
          </span>
          <button
            className="patterns-continue-btn ops-navbar-cta"
            onClick={onContinue}
          >
            Continue → Choose Your Questline
          </button>
        </div>

        {/* Live update banner */}
        {isAnalyzing && (
          <div style={{
            position: 'sticky', top: 49, zIndex: 9,
            background: '#F59E0B22', borderBottom: '1px solid #F59E0B44',
            padding: '0.5rem 1rem', fontSize: '0.8rem', color: '#F59E0B',
            display: 'flex', alignItems: 'center', gap: '0.5rem',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#F59E0B', display: 'inline-block', flexShrink: 0 }} />
            {changedDomain ? `Reanalyzing ${changedDomain} patterns...` : 'Reanalyzing patterns...'}
          </div>
        )}

        {/* Main content */}
        <div style={{
          maxWidth: '900px',
          margin: '0 auto',
          padding: '3rem 2rem 6rem',
        }}>
          {/* Page header */}
          <div style={{ marginBottom: '2.5rem' }}>
            <h1 style={{
              fontSize: 'clamp(1.6rem, 4vw, 2.2rem)',
              fontWeight: 800,
              color: '#fff',
              margin: '0 0 0.5rem',
              lineHeight: 1.2,
            }}>
              Patterns in Your Data, Insights for Your Future
            </h1>
            <p style={{ color: '#666', fontSize: '15px', margin: 0 }}>
              Cross-domain correlations are patterns no single app can surface
            </p>
          </div>

          {/* Loading state */}
          {patterns === null && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {[0, 1, 2].map((i) => (
                <div key={i} style={{ ...skeletonStyle, animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
          )}

          {/* Cross-domain patterns — full width */}
          {patterns !== null && crossDomain.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <div style={{
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.1em',
                color: '#F59E0B',
                textTransform: 'uppercase',
                marginBottom: '12px',
              }}>
                Cross-Domain Insights
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {crossDomain.map((p, i) => {
                  const isPulsing = isAnalyzing && changedDomain != null && p.domains.includes(changedDomain);
                  return (
                    <div key={p.id} style={isPulsing ? {
                      borderRadius: '12px',
                      boxShadow: '0 0 0 2px #F59E0B66',
                      animation: 'amberPulse 1.5s ease-in-out infinite',
                    } : undefined}>
                      <PatternCard pattern={p} index={i} />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Single-domain patterns — 2-column grid */}
          {patterns !== null && singleDomain.length > 0 && (
            <div>
              <div style={{
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.1em',
                color: '#555',
                textTransform: 'uppercase',
                marginBottom: '12px',
              }}>
                Domain Patterns
              </div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
                gap: '12px',
              }}>
                {singleDomain.map((p, i) => {
                  const isPulsing = isAnalyzing && changedDomain != null && p.domains.includes(changedDomain);
                  return (
                    <div key={p.id} style={isPulsing ? {
                      borderRadius: '12px',
                      boxShadow: '0 0 0 2px #F59E0B66',
                      animation: 'amberPulse 1.5s ease-in-out infinite',
                    } : undefined}>
                      <PatternCard pattern={p} index={crossDomain.length + i} />
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Sticky bottom CTA */}
        <div style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          background: 'rgba(10,10,15,0.95)',
          backdropFilter: 'blur(12px)',
          borderTop: '1px solid rgba(255,255,255,0.06)',
          padding: '16px 24px',
          display: 'flex',
          justifyContent: 'center',
        }}>
          <button
            className="patterns-continue-btn ops-navbar-cta"
            onClick={onContinue}
            style={{ padding: '0.6rem 2rem', fontSize: '0.65rem' }}
          >
            Continue → Choose Your Questline
          </button>
        </div>
      </div>
    </>
  );
}
