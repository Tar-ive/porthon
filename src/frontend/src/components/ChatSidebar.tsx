import { useEffect, useState, useRef } from 'react';

interface Quest {
    action: string;
    rationale: string;
    data_ref: string;
    compound_summary: string;
}

interface ApprovalItem {
    approval_id: string;
    task_id: string;
    worker_id: string;
    reason: string;
}

interface EventItem {
    type: string;
    payload: Record<string, unknown>;
    ts: string;
}

const DEMO_TOKEN = 'Bearer sk_demo_default';

export default function ChatSidebar({ quests }: { quests: Quest[] }) {
    const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
    const [events, setEvents] = useState<EventItem[]>([]);
    const eventsRef = useRef<EventItem[]>([]);

    // Fetch approvals
    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch('/v1/approvals', {
                    headers: { Authorization: DEMO_TOKEN },
                });
                const body = await res.json();
                setApprovals(body.approvals || []);
            } catch {
                // silent
            }
        };
        load();
        const interval = setInterval(load, 5000);
        return () => clearInterval(interval);
    }, []);

    // SSE events
    useEffect(() => {
        const es = new EventSource('/v1/events/stream');
        es.onmessage = (msg) => {
            try {
                const evt = JSON.parse(msg.data);
                const item: EventItem = {
                    type: evt.type || 'event',
                    payload: evt.payload || {},
                    ts: new Date().toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                    }),
                };
                eventsRef.current = [item, ...eventsRef.current].slice(0, 15);
                setEvents([...eventsRef.current]);
            } catch {
                // ignore
            }
        };
        return () => es.close();
    }, []);

    const resolveApproval = async (
        approvalId: string,
        decision: 'approved' | 'rejected'
    ) => {
        try {
            await fetch('/v1/approvals/resolve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: DEMO_TOKEN,
                },
                body: JSON.stringify({ approval_id: approvalId, decision }),
            });
            setApprovals((prev) =>
                prev.filter((a) => a.approval_id !== approvalId)
            );
        } catch {
            // silent
        }
    };

    // Humanize event type
    const humanize = (type: string) =>
        type
            .replace(/^demo\./, '')
            .replace(/\./g, ' › ')
            .replace(/_/g, ' ');

    return (
        <aside className="chat-sidebar">
            <div className="chat-sidebar-section">
                <div className="chat-sidebar-header">
                    <span>Why Questline</span>
                </div>
                <div className="chat-sidebar-items">
                    <div className="chat-sidebar-note">
                        Questline is built for freelancers who lose revenue in tiny gaps: slow follow-ups, overloaded weeks, and inbound demand that never turns into booked work.
                    </div>
                    <div className="chat-sidebar-item">
                        <span className="chat-sidebar-item-num">01</span>
                        <span className="chat-sidebar-item-text">Catch leads before they cool off or disappear behind delivery work.</span>
                    </div>
                    <div className="chat-sidebar-item">
                        <span className="chat-sidebar-item-num">02</span>
                        <span className="chat-sidebar-item-text">Turn live signals into next actions Theo can actually execute today.</span>
                    </div>
                    <div className="chat-sidebar-item">
                        <span className="chat-sidebar-item-num">03</span>
                        <span className="chat-sidebar-item-text">Balance pipeline urgency against time pressure so growth does not break delivery.</span>
                    </div>
                </div>
            </div>

            <div className="chat-sidebar-section">
                <div className="chat-sidebar-header">
                    <span>Agent Roles</span>
                </div>
                <div className="chat-sidebar-items">
                    <div className="chat-sidebar-role">
                        <div className="chat-sidebar-role-label">Reactive agents</div>
                        <div className="chat-sidebar-role-text">
                            Watch Notion, approvals, calendar pressure, and incoming demand so the operating picture updates the moment Theo&apos;s world changes.
                        </div>
                    </div>
                    <div className="chat-sidebar-role">
                        <div className="chat-sidebar-role-label">Proactive agents</div>
                        <div className="chat-sidebar-role-text">
                            Convert those changes into follow-ups, focus blocks, pricing nudges, and outreach sequences that keep revenue moving.
                        </div>
                    </div>
                </div>
            </div>

            {/* Follow-ups from quest actions */}
            {quests.length > 0 && (
                <div className="chat-sidebar-section">
                    <div className="chat-sidebar-header">
                        <span>Follow-ups</span>
                        <span className="chat-sidebar-count">{quests.length}</span>
                    </div>
                    <div className="chat-sidebar-items">
                        {quests.slice(0, 5).map((q, i) => (
                            <div key={i} className="chat-sidebar-item">
                                <span className="chat-sidebar-item-num">
                                    Q{String(i + 1).padStart(2, '0')}
                                </span>
                                <span className="chat-sidebar-item-text">{q.action}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Approvals */}
            <div className="chat-sidebar-section">
                <div className="chat-sidebar-header">
                    <span>Approvals</span>
                    <span className="chat-sidebar-count">{approvals.length}</span>
                </div>
                <div className="chat-sidebar-items">
                    {approvals.length === 0 ? (
                        <div className="chat-sidebar-empty">No pending approvals</div>
                    ) : (
                        approvals.map((a) => (
                            <div key={a.approval_id} className="chat-sidebar-approval">
                                <div className="chat-sidebar-approval-reason">{a.reason}</div>
                                <div className="chat-sidebar-approval-meta">
                                    {a.worker_id}
                                </div>
                                <div className="chat-sidebar-approval-actions">
                                    <button
                                        className="approval-btn approval-btn--approve"
                                        onClick={() =>
                                            resolveApproval(a.approval_id, 'approved')
                                        }
                                    >
                                        ✓
                                    </button>
                                    <button
                                        className="approval-btn approval-btn--reject"
                                        onClick={() =>
                                            resolveApproval(a.approval_id, 'rejected')
                                        }
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Notifications (SSE events) */}
            <div className="chat-sidebar-section chat-sidebar-section--grow">
                <div className="chat-sidebar-header">
                    <span>Notifications</span>
                    {events.length > 0 && (
                        <span className="chat-sidebar-live-dot" />
                    )}
                </div>
                <div className="chat-sidebar-items chat-sidebar-events">
                    {events.length === 0 ? (
                        <div className="chat-sidebar-empty">Awaiting events…</div>
                    ) : (
                        events.map((evt, i) => (
                            <div
                                key={`${evt.ts}-${i}`}
                                className="chat-sidebar-event"
                                style={{ opacity: 1 - i * 0.06 }}
                            >
                                <span className="chat-sidebar-event-dot">●</span>
                                <span className="chat-sidebar-event-text">
                                    {humanize(evt.type)}
                                </span>
                                <span className="chat-sidebar-event-ts">{evt.ts}</span>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </aside>
    );
}
