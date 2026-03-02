import { useState } from 'react';

interface Scenario {
  id: string;
  title: string;
  horizon: string;
  likelihood: 'most_likely' | 'possible' | 'aspirational';
  summary: string;
  tags: string[];
  pattern_ids: string[];
}

const LIKELIHOOD_ICON: Record<string, string> = {
  most_likely: '◈',
  possible: '◇',
  aspirational: '✦',
};

const LIKELIHOOD_LABEL: Record<string, string> = {
  most_likely: 'Most Likely',
  possible: 'Possible',
  aspirational: 'Aspirational',
};

const LIKELIHOOD_CLASS: Record<string, string> = {
  most_likely: 'badge--likely',
  possible: 'badge--possible',
  aspirational: 'badge--aspirational',
};

type Phase = 'idle' | 'loading' | 'ready';

interface Props {
  onSelect: (scenario: Scenario) => void;
}

export default function ScenarioSelect({ onSelect }: Props) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [hovered, setHovered] = useState<string | null>(null);

  const handleGenerate = async () => {
    setPhase('loading');
    try {
      const res = await fetch('/api/scenarios');
      const data = await res.json();
      setScenarios(data);
      setPhase('ready');
    } catch {
      setPhase('idle');
    }
  };

  return (
    <div className="scenario-root">
      <div className="scenario-header">
        <div className="scenario-wordmark">Questline</div>
        <div className="scenario-persona">Theo Nakamura · p05</div>
        <p className="scenario-lead">
          The Oracle will analyze your behavioral data across finance, calendar, and social
          signals to project your life 1, 5, and 10 years out.
        </p>
      </div>

      {phase === 'idle' && (
        <div className="scenario-idle">
          <button className="generate-btn" onClick={handleGenerate}>
            <span className="generate-btn-icon">◈</span>
            Generate My Trajectories
          </button>
          <p className="generate-hint">Takes ~10 seconds · powered by behavioral pattern analysis</p>
        </div>
      )}

      {phase === 'loading' && (
        <div className="scenario-loading-full">
          <div className="loading-orb">
            <span className="loading-rune">✦</span>
          </div>
          <div className="loading-label">Analyzing patterns</div>
          <div className="loading-steps">
            <LoadingStep delay={0}>Parsing financial signals</LoadingStep>
            <LoadingStep delay={1.2}>Cross-referencing calendar data</LoadingStep>
            <LoadingStep delay={2.5}>Projecting life trajectories</LoadingStep>
          </div>
        </div>
      )}

      {phase === 'ready' && (
        <>
          <div className="scenario-grid">
            {scenarios.map((s, i) => (
              <button
                key={s.id}
                className={`scenario-card ${hovered === s.id ? 'scenario-card--hovered' : ''}`}
                style={{ animationDelay: `${i * 0.12}s` }}
                onMouseEnter={() => setHovered(s.id)}
                onMouseLeave={() => setHovered(null)}
                onClick={() => onSelect(s)}
              >
                <div className="sc-top">
                  <span className="sc-icon">{LIKELIHOOD_ICON[s.likelihood]}</span>
                  <div className="sc-badges">
                    <span className={`badge ${LIKELIHOOD_CLASS[s.likelihood]}`}>
                      {LIKELIHOOD_LABEL[s.likelihood]}
                    </span>
                    <span className="badge badge--horizon">{s.horizon}</span>
                  </div>
                </div>
                <div className="sc-title">{s.title}</div>
                <div className="sc-summary">{s.summary}</div>
                <div className="sc-tags">
                  {s.tags.map((t) => (
                    <span key={t} className="sc-tag">#{t}</span>
                  ))}
                </div>
                <div className="sc-arrow">Explore this path →</div>
              </button>
            ))}
          </div>

          <div className="scenario-footer">
            <span className="scenario-footer-text">
              ◈ Powered by behavioral pattern analysis across finance, calendar &amp; social signals
            </span>
          </div>
        </>
      )}
    </div>
  );
}

function LoadingStep({ children, delay }: { children: string; delay: number }) {
  return (
    <div className="loading-step" style={{ animationDelay: `${delay}s` }}>
      <span className="loading-step-dot" />
      {children}
    </div>
  );
}
