import { useEffect, useState } from 'react';
import { useAgentStream } from '../../hooks/useAgentStream';

export default function DaemonBar() {
    const { isAnalyzing, analysisMessage, changedDomain, scenariosVersion, lastEvent, lastNotionRefresh, lastSource } = useAgentStream();
    const [lastUpdated, setLastUpdated] = useState<string | null>(null);
    const [flash, setFlash] = useState(false);

    useEffect(() => {
        if (scenariosVersion > 0) {
            setLastUpdated(
                new Date().toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                })
            );
            setFlash(true);
            const t = setTimeout(() => setFlash(false), 2500);
            return () => clearTimeout(t);
        }
    }, [scenariosVersion]);

    const state: 'analyzing' | 'updated' | 'idle' = isAnalyzing
        ? 'analyzing'
        : flash
        ? 'updated'
        : 'idle';

    const notionRefreshLabel =
        lastEvent?.type === 'notion_leads_refreshed' && lastNotionRefresh
            ? `Live Notion refresh mirrored ${lastNotionRefresh.leadCount} leads`
            : null;

    const label = state === 'analyzing'
        ? (
            lastSource === 'live_webhook'
                ? (analysisMessage ?? `Analyzing ${changedDomain ?? 'notion_leads'} from live webhook…`)
                : (analysisMessage ?? `Analyzing ${changedDomain ?? 'data'}…`)
        )
        : state === 'updated'
        ? (notionRefreshLabel ?? 'Trajectories updated')
        : 'Daemon running';

    return (
        <div className={`daemon-bar daemon-bar--${state}`}>
            <span className={`daemon-dot daemon-dot--${state}`} />
            <span className="daemon-label">{label}</span>
            <span className="daemon-sep">·</span>
            <span className="daemon-meta">AlwaysOnMaster</span>
            <span className="daemon-sep">·</span>
            <span className="daemon-meta">15 min tick + event-triggered</span>
            {lastUpdated && (
                <>
                    <span className="daemon-sep">·</span>
                    <span className="daemon-meta">last analysis {lastUpdated}</span>
                </>
            )}
            <span className="daemon-spacer" />
            <span className="daemon-workers">6 workers active</span>
        </div>
    );
}
