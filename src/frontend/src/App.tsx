import { useState } from 'react';
import Chat from './Chat';
import ScenarioSelect from './ScenarioSelect';

interface Scenario {
  id: string;
  title: string;
  horizon: string;
  likelihood: string;
  summary: string;
  tags: string[];
}

function App() {
  const [scenario, setScenario] = useState<Scenario | null>(null);

  if (!scenario) {
    return <ScenarioSelect onSelect={setScenario} />;
  }

  return <Chat scenario={scenario} />;
}

export default App;
