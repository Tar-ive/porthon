/**
 * useAgentStream — returns live agent stream state.
 *
 * Reads from AgentStreamContext (one shared SSE connection for the whole app).
 * Components do NOT open their own SSE connections; the provider owns the
 * single connection opened in AgentStreamContext.tsx.
 */

import { useAgentStreamContext } from '../contexts/AgentStreamContext';

export interface AgentStreamEvent {
    type: string;
    payload?: Record<string, unknown>;
    created_at?: string;
}

export interface AgentStreamState {
    lastEvent: AgentStreamEvent | null;
    isAnalyzing: boolean;
    changedDomain: string | null;
    scenariosVersion: number;
    actionsVersion: number;
    analysisMessage: string | null;
    lastSource: string | null;
    lastNotionRefresh: {
        eventId: string | null;
        leadCount: number;
        changedDomains: string[];
    } | null;
}

export function useAgentStream(): AgentStreamState {
    return useAgentStreamContext();
}
