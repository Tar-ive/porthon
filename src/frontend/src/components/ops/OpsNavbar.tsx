import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

export default function OpsNavbar() {
    const [opsCount, setOpsCount] = useState(847);

    useEffect(() => {
        const id = setInterval(() => {
            setOpsCount((prev) => prev + Math.floor(Math.random() * 5) + 1);
        }, 4000);
        return () => clearInterval(id);
    }, []);

    return (
        <nav className="ops-navbar">
            <div className="ops-navbar-brand">
                <span className="ops-navbar-dot" />
                QUESTLINE
            </div>

            <span className="ops-navbar-counter">
                {opsCount.toLocaleString()} ops processed
            </span>

            <div className="ops-navbar-links">
                <Link to="/" className="ops-navbar-link">Dashboard</Link>
                <Link to="/app" className="ops-navbar-link">Quest</Link>
                <Link to="/app" className="ops-navbar-cta">Begin Your Quest</Link>
            </div>
        </nav>
    );
}
