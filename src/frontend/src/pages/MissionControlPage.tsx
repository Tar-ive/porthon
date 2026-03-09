import OpsNavbar from '../components/ops/OpsNavbar';
import MissionControl from './MissionControl';

// Wrapper that gives MissionControl its own standalone route at /ops
// The existing MissionControl component requires scenario + onDeploy props
// For /ops we pass a dummy scenario and no-op onDeploy
const DEMO_SCENARIO = {
  id: 'demo',
  title: 'Ops View — System Monitor',
  horizon: 'live',
  likelihood: 'most_likely',
  summary: 'Live system operations view',
  tags: ['ops'],
};

export default function MissionControlPage() {
  return (
    <div>
      <OpsNavbar />
      <MissionControl scenario={DEMO_SCENARIO} onDeploy={() => {}} />
    </div>
  );
}
