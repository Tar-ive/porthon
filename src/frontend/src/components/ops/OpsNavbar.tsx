import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAgentStream } from '../../hooks/useAgentStream';

export default function OpsNavbar() {
    const [opsCount, setOpsCount] = useState(847);
    const { isAnalyzing, scenariosVersion } = useAgentStream();
    const [flash, setFlash] = useState(false);

    useEffect(() => {
        const id = setInterval(() => {
            setOpsCount((prev) => prev + Math.floor(Math.random() * 5) + 1);
        }, 4000);
        return () => clearInterval(id);
    }, []);

    useEffect(() => {
        if (scenariosVersion > 0) {
            setFlash(true);
            const t = setTimeout(() => setFlash(false), 2500);
            return () => clearTimeout(t);
        }
    }, [scenariosVersion]);

    const dotState = isAnalyzing ? 'analyzing' : flash ? 'updated' : 'idle';

    return (
        <nav className="ops-navbar">
            <div className="ops-navbar-brand">
                <span className={`ops-navbar-dot ops-navbar-dot--${dotState}`} />
                QUESTLINE
            </div>

            <div className="ops-navbar-daemon">
                <span className={`ops-daemon-dot ops-daemon-dot--${dotState}`} />
                <span className="ops-daemon-label">
                    {isAnalyzing ? 'analyzing…' : flash ? 'updated' : 'daemon running'}
                </span>
            </div>

            <span className="ops-navbar-counter">
                {opsCount.toLocaleString()} ops processed
            </span>

            <div className="ops-navbar-links">
                <Link to="/" className="ops-navbar-link">Dashboard</Link>
                <Link to="/ops" className="ops-navbar-link">Ops View</Link>
                <Link to="/app" className="ops-navbar-cta">Current Questline</Link>
            </div>
        </nav>
    );
}
