import '../dashboard.css';
import AnimatedKnowledgeGraph from '../components/ops/AnimatedKnowledgeGraph';
import WorkerFleet from '../components/ops/WorkerFleet';
import TelemetryFeed from '../components/ops/TelemetryFeed';
import ApprovalQueue from '../components/ops/ApprovalQueue';

interface Scenario {
    id: string;
    title: string;
    horizon: string;
    likelihood: string;
    summary: string;
    tags: string[];
}

export default function MissionControl({
    scenario,
    onDeploy,
}: {
    scenario: Scenario;
    onDeploy: () => void;
}) {
    return (
        <div className="mission-root">
            {/* Scenario title bar */}
            <div className="mission-scenario-bar">
                <span className="mission-scenario-title">{scenario.title}</span>
                <span className="mission-scenario-horizon">{scenario.horizon}</span>
            </div>

            {/* Main grid: KG + telemetry left, workers + approvals right */}
            <div className="mission-grid">
                <div className="mission-left-col">
                    <AnimatedKnowledgeGraph />
                    <TelemetryFeed />
                </div>
                <div className="mission-sidebar">
                    <WorkerFleet />
                    <ApprovalQueue />
                </div>
            </div>

            {/* Deploy button */}
            <div className="mission-footer">
                <button className="mission-deploy-btn" onClick={onDeploy}>
                    Deploy Agents → Chat
                </button>
            </div>
        </div>
    );
}
