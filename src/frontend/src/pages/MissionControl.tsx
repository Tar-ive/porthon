import '../dashboard.css';
import AnimatedKnowledgeGraph from '../components/ops/AnimatedKnowledgeGraph';
import WorkerFleet from '../components/ops/WorkerFleet';
import TelemetryFeed from '../components/ops/TelemetryFeed';
import ApprovalQueue from '../components/ops/ApprovalQueue';
import DaemonBar from '../components/ops/DaemonBar';
import DemoFeed from '../components/ops/DemoFeed';

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
            <div className="mission-scenario-bar">
                <span className="mission-scenario-title">{scenario.title}</span>
                <span className="mission-scenario-horizon">{scenario.horizon}</span>
            </div>

            <section className="mission-thesis">
                <div className="mission-thesis-copy">
                    <div className="mission-thesis-kicker">Freelance Revenue Operating System</div>
                    <h1 className="mission-thesis-title">
                        Questline helps Theo catch cooling leads, protect delivery capacity, and convert weak signals into booked work.
                    </h1>
                    <p className="mission-thesis-text">
                        Reactive agents watch live pipeline, schedule, and demand changes. Proactive agents turn those shifts into follow-ups, focus blocks, and revenue-preserving moves before momentum slips.
                    </p>
                </div>
                <div className="mission-thesis-grid">
                    <article className="mission-thesis-card">
                        <span className="mission-thesis-card-label">Reactive Agents</span>
                        <p className="mission-thesis-card-text">
                            Surface hot lead movement, missed follow-ups, and delivery pressure the moment Notion or the live feed changes.
                        </p>
                    </article>
                    <article className="mission-thesis-card">
                        <span className="mission-thesis-card-label">Proactive Agents</span>
                        <p className="mission-thesis-card-text">
                            Queue the next outreach, tighten the week around deadlines, and keep Theo shipping while revenue stays in motion.
                        </p>
                    </article>
                    <article className="mission-thesis-card">
                        <span className="mission-thesis-card-label">Freelancer Outcome</span>
                        <p className="mission-thesis-card-text">
                            Fewer dropped deals, faster follow-through, clearer pricing pressure, and less guessing about what to do next.
                        </p>
                    </article>
                </div>
            </section>

            <DaemonBar />

            <div className="mission-grid">
                <div className="mission-left-col">
                    <AnimatedKnowledgeGraph />
                    <TelemetryFeed />
                </div>
                <div className="mission-sidebar">
                    <WorkerFleet />
                    <DemoFeed />
                    <ApprovalQueue />
                </div>
            </div>

            <div className="mission-footer">
                <button className="mission-deploy-btn" onClick={onDeploy}>
                    Deploy Agents → Chat
                </button>
            </div>
        </div>
    );
}
