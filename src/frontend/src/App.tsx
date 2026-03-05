import { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import Chat from './Chat';
import ScenarioSelect from './ScenarioSelect';
import Dashboard from './pages/Dashboard';
import MissionControl from './pages/MissionControl';

interface Scenario {
  id: string;
  title: string;
  horizon: string;
  likelihood: string;
  summary: string;
  tags: string[];
}

function AppFlow() {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [deployed, setDeployed] = useState(false);

  if (!scenario) {
    return <ScenarioSelect onSelect={setScenario} />;
  }

  if (!deployed) {
    return <MissionControl scenario={scenario} onDeploy={() => setDeployed(true)} />;
  }

  return <Chat scenario={scenario} />;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/app" element={<AppFlow />} />
    </Routes>
  );
}

export default App;
