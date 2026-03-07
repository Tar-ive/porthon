import { useEffect, useRef, useState } from 'react';

export interface AgentStreamEvent {
  type: string;
  payload?: Record<string, unknown>;
  created_at?: string;
}

export interface AgentStreamState {
  /** Most recent raw event */
  lastEvent: AgentStreamEvent | null;
  /** True while analysis_running event is active (cleared by scenarios_updated or analysis_error) */
  isAnalyzing: boolean;
  /** Domain that triggered the last data_changed event */
  changedDomain: string | null;
  /** Increments each time scenarios_updated fires — trigger a refetch in consumers */
  scenariosVersion: number;
  /** Increments each time actions_updated fires — trigger a quest re-fetch in Chat */
  actionsVersion: number;
  /** Message from analysis_running */
  analysisMessage: string | null;
}

/**
 * Subscribe to /api/agent/stream (SSE) and return reactive state.
 * Automatically reconnects on error after a short delay.
 */
export function useAgentStream(): AgentStreamState {
  const [state, setState] = useState<AgentStreamState>({
    lastEvent: null,
    isAnalyzing: false,
    changedDomain: null,
    scenariosVersion: 0,
    actionsVersion: 0,
    analysisMessage: null,
  });

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
          const evt = JSON.parse(msg.data) as AgentStreamEvent;
          setState((prev) => {
            const next: AgentStreamState = { ...prev, lastEvent: evt };

            switch (evt.type) {
              case 'data_changed':
                next.changedDomain = (evt.payload?.domain as string) ?? null;
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
                next.isAnalyzing = false;
                next.analysisMessage = null;
                break;

              case 'analysis_error':
                next.isAnalyzing = false;
                next.analysisMessage = null;
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

  return state;
}
