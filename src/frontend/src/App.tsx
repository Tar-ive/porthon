import React, { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import Chat from './Chat';
import ScenarioSelect from './ScenarioSelect';
import Dashboard from './pages/Dashboard';
import MissionControlPage from './pages/MissionControlPage';
import IngestScreen from './pages/IngestScreen';
import PatternsScreen from './pages/PatternsScreen';
import ActionsScreen from './pages/ActionsScreen';

interface Scenario {
  id: string;
  title: string;
  horizon: string;
  likelihood: string;
  summary: string;
  tags: string[];
}

interface Action {
  id: string;
  action: string;
  title?: string;
  data_ref: string;
  pattern_id?: string;
  rationale: string;
  compound_summary: string;
}

type AppStep = 'ingest' | 'patterns' | 'questlines' | 'actions' | 'chat';

const STEPS: AppStep[] = ['ingest', 'patterns', 'questlines', 'actions', 'chat'];
const STEP_LABELS: Record<AppStep, string> = {
  ingest: 'Ingest',
  patterns: 'Patterns',
  questlines: 'Questlines',
  actions: 'Actions',
  chat: 'Chat',
};

function ProgressIndicator({ step }: { step: AppStep }) {
  const currentIndex = STEPS.indexOf(step);
  return (
    <div style={{
      position: 'fixed',
      top: '1rem',
      left: '50%',
      transform: 'translateX(-50%)',
      display: 'flex',
      gap: '0.5rem',
      alignItems: 'center',
      zIndex: 100,
      background: 'rgba(10,10,15,0.8)',
      backdropFilter: 'blur(8px)',
      padding: '0.4rem 0.75rem',
      borderRadius: '999px',
      border: '1px solid #1a1a2e',
    }}>
      {STEPS.map((s, i) => (
        <div key={s} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div
            title={STEP_LABELS[s]}
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: s === step ? '#7B61FF' : currentIndex > i ? '#7B61FF44' : '#333',
              transition: 'background 300ms ease',
            }}
          />
          {i < STEPS.length - 1 && (
            <div style={{ width: '20px', height: '1px', background: currentIndex > i ? '#7B61FF44' : '#222' }} />
          )}
        </div>
      ))}
    </div>
  );
}

function AppFlow() {
  const [step, setStep] = useState<AppStep>(() => {
    return (sessionStorage.getItem('appStep') as AppStep) || 'ingest';
  });

  const [scenario, setScenario] = useState<Scenario | null>(() => {
    const stored = sessionStorage.getItem('appScenario');
    if (stored) {
      try {
        return JSON.parse(stored) as Scenario;
      } catch {
        return null;
      }
    }
    return null;
  });

  const [actions, setActions] = useState<Action[]>(() => {
    const stored = sessionStorage.getItem('appActions');
    if (stored) {
      try {
        return JSON.parse(stored) as Action[];
      } catch {
        return [];
      }
    }
    return [];
  });

  useEffect(() => {
    sessionStorage.setItem('appStep', step);
  }, [step]);

  useEffect(() => {
    if (scenario) {
      sessionStorage.setItem('appScenario', JSON.stringify(scenario));
    } else {
      sessionStorage.removeItem('appScenario');
    }
  }, [scenario]);

  let screen: React.ReactNode;

  if (step === 'ingest') {
    screen = <IngestScreen onContinue={() => setStep('patterns')} />;
  } else if (step === 'patterns') {
    screen = <PatternsScreen onContinue={() => setStep('questlines')} />;
  } else if (step === 'questlines') {
    screen = (
      <ScenarioSelect
        onSelect={(s) => {
          setScenario(s);
          setStep('actions');
        }}
      />
    );
  } else if (step === 'actions') {
    screen = <ActionsScreen scenario={scenario} onContinue={() => {
      const stored = sessionStorage.getItem('appActions');
      if (stored) {
        try { setActions(JSON.parse(stored) as Action[]); } catch { /* ignore */ }
      }
      setStep('chat');
    }} />;
  } else {
    // step === 'chat'
    if (!scenario) return null;
    screen = (
      <Chat
        scenario={scenario}
        actions={actions}
        onRestart={() => {
          sessionStorage.removeItem('appStep');
          sessionStorage.removeItem('appScenario');
          sessionStorage.removeItem('appActions');
          setStep('ingest');
          setScenario(null);
          setActions([]);
        }}
      />
    );
  }

  return (
    <>
      {step !== 'ingest' && <ProgressIndicator step={step} />}
      <div key={step} className="app-screen">
        {screen}
      </div>
    </>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/app" element={<AppFlow />} />
      <Route path="/ops" element={<MissionControlPage />} />
    </Routes>
  );
}

export default App;
