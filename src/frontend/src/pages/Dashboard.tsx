import '../dashboard.css';
import OpsNavbar from '../components/ops/OpsNavbar';
import DataSummary from '../components/ops/DataSummary';
import KGInsights from '../components/ops/KGInsights';
import RecentActivity from '../components/ops/RecentActivity';

export default function Dashboard() {
    return (
        <div className="dashboard-root">
            <OpsNavbar />
            <DataSummary />
            <div className="dashboard-data-grid">
                <KGInsights />
                <RecentActivity />
            </div>
        </div>
    );
}
