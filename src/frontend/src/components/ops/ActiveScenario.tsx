import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface RuntimeState {
    active_scenario?: {
        scenario_id?: string;
        title?: string;
        horizon?: string;
        likelihood?: string;
        summary?: string;
    } | null;
}

const DEMO_TOKEN = 'Bearer sk_demo_default';

export default function ActiveScenario() {
    const [runtime, setRuntime] = useState<RuntimeState | null>(null);

    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch('/v1/runtime', {
                    headers: { Authorization: DEMO_TOKEN },
                });
                const body = await res.json();
                setRuntime(body);
            } catch {
                // silent
            }
        };
        load();
        const id = setInterval(load, 10000);
        return () => clearInterval(id);
    }, []);

    const scenario = runtime?.active_scenario;

    if (!scenario) {
        return (
            <div className="scenario-bar scenario-bar--active">
                <span className="scenario-bar-title" style={{ color: 'var(--muted)' }}>
                    No active quest
                </span>
                <Link to="/app" className="ops-navbar-cta" style={{ marginLeft: 'auto' }}>
                    Begin Your Quest
                </Link>
            </div>
        );
    }

    return (
        <div className="scenario-bar scenario-bar--active">
            <span className="scenario-bar-title">{scenario.title}</span>
            {scenario.horizon && (
                <span className="scenario-bar-horizon">{scenario.horizon}</span>
            )}
            {scenario.summary && (
                <span className="scenario-bar-summary">{scenario.summary}</span>
            )}
        </div>
    );
}
