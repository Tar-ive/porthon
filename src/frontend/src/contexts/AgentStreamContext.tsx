/**
 * AgentStreamContext — single shared SSE connection for /api/agent/stream.
 *
 * Wrap the app with <AgentStreamProvider> once. All consumers call
 * useAgentStream() which reads from context instead of opening their
 * own SSE connection. This keeps concurrent SSE connections at 1
 * (+ 1 for TelemetryFeed's event log) instead of one per component.
 */

import { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { AgentStreamState } from '../hooks/useAgentStream';

const defaultState: AgentStreamState = {
    lastEvent: null,
    isAnalyzing: false,
    changedDomain: null,
    scenariosVersion: 0,
    actionsVersion: 0,
    analysisMessage: null,
    lastSource: null,
    lastNotionRefresh: null,
};

const AgentStreamContext = createContext<AgentStreamState>(defaultState);

export function AgentStreamProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<AgentStreamState>(defaultState);
    const sseRef = useRef<EventSource | null>(null);
    const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        let cancelled = false;

        const connect = () => {
            if (cancelled) return;
            const source = new EventSource('/api/agent/stream');
            sseRef.current = source;

            source.onmessage = (msg) => {
                try {
                    const evt = JSON.parse(msg.data) as AgentStreamState['lastEvent'];
                    if (!evt || !evt.type) return;
                    setState((prev) => {
                        const next: AgentStreamState = { ...prev, lastEvent: evt };
                        switch (evt.type) {
                            case 'data_changed':
                                next.changedDomain = (evt.payload?.domain as string) ?? null;
                                next.lastSource = (evt.payload?.source as string) ?? null;
                                next.isAnalyzing = true;
                                next.analysisMessage = `New ${next.changedDomain ?? ''} data detected`;
                                break;
                            case 'analysis_running':
                                next.isAnalyzing = true;
                                next.analysisMessage = (evt.payload?.message as string) ?? 'Re-analyzing…';
                                break;
                            case 'scenarios_updated':
                                next.isAnalyzing = false;
                                next.analysisMessage = null;
                                next.scenariosVersion = prev.scenariosVersion + 1;
                                break;
                            case 'actions_updated':
                                next.isAnalyzing = false;
                                next.analysisMessage = null;
                                next.actionsVersion = prev.actionsVersion + 1;
                                break;
                            case 'analysis_stable':
                            case 'analysis_error':
                                next.isAnalyzing = false;
                                next.analysisMessage = null;
                                break;
                            case 'notion_leads_refreshed':
                                next.lastSource = 'live_webhook';
                                next.lastNotionRefresh = {
                                    eventId: (evt.payload?.event_id as string) ?? null,
                                    leadCount: Number(evt.payload?.lead_count ?? 0),
                                    changedDomains: Array.isArray(evt.payload?.changed_domains)
                                        ? (evt.payload?.changed_domains as string[])
                                        : [],
                                };
                                break;
                        }
                        return next;
                    });
                } catch {
                    // skip non-JSON keepalives
                }
            };

            source.onerror = () => {
                source.close();
                sseRef.current = null;
                if (!cancelled) {
                    reconnectTimer.current = setTimeout(connect, 3000);
                }
            };
        };

        connect();

        return () => {
            cancelled = true;
            if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
            sseRef.current?.close();
        };
    }, []);

    return (
        <AgentStreamContext.Provider value={state}>
            {children}
        </AgentStreamContext.Provider>
    );
}

export function useAgentStreamContext(): AgentStreamState {
    return useContext(AgentStreamContext);
}
