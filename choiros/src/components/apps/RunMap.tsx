import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, Play, Pause } from 'lucide-react';
import { authFetch } from '../../lib/auth';
import { useAgent, type AgentMessage } from '../../hooks/useAgent';
import './RunMap.css';

const SUPERVISOR_URL = import.meta.env.VITE_SUPERVISOR_URL || 'http://localhost:8001';

interface RunSummary {
    id: string;
    status: string;
    mode?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
    started_at?: string | null;
    finished_at?: string | null;
    prompt?: string | null;
    work_item_status?: string | null;
}

interface RunInput {
    id: string;
    run_id: string;
    prompt: string;
    kind: string;
    created_at: string;
}

interface RunTimelineEvent {
    seq: number;
    type: string;
    timestamp: string;
    payload: Record<string, unknown>;
}

interface RunTimelineResponse {
    run: RunSummary | null;
    inputs: RunInput[];
    events: RunTimelineEvent[];
    notes: Array<Record<string, unknown>>;
    verifications: Array<Record<string, unknown>>;
}

interface RunMapProps {
    runId?: string;
}

function formatTime(value?: string | null) {
    if (!value) return '—';
    try {
        return new Date(value).toLocaleTimeString();
    } catch {
        return value;
    }
}

export function RunMap({ runId }: RunMapProps) {
    const [runs, setRuns] = useState<RunSummary[]>([]);
    const [selectedRunId, setSelectedRunId] = useState<string | null>(runId ?? null);
    const [timeline, setTimeline] = useState<RunTimelineResponse | null>(null);
    const [isLoadingRuns, setIsLoadingRuns] = useState(false);
    const [isLoadingTimeline, setIsLoadingTimeline] = useState(false);
    const [isLive, setIsLive] = useState(true);
    const [followup, setFollowup] = useState('');

    const { sendPrompt } = useAgent({
        onMessage: (message: AgentMessage) => {
            if (message.type === 'enqueued' && typeof message.content === 'object' && message.content) {
                const nextRunId = (message.content as { run_id?: string }).run_id;
                if (nextRunId) {
                    setSelectedRunId(nextRunId);
                }
            }
        },
    });

    const fetchRuns = useCallback(async () => {
        setIsLoadingRuns(true);
        try {
            const res = await authFetch(`${SUPERVISOR_URL}/runs?limit=100`);
            if (!res.ok) {
                throw new Error('Failed to load runs');
            }
            const data = (await res.json()) as { runs: RunSummary[] };
            setRuns(data.runs);
            if (!selectedRunId && data.runs.length > 0) {
                setSelectedRunId(data.runs[0].id);
            }
        } catch (err) {
            console.error('[RunMap] Failed to fetch runs:', err);
        } finally {
            setIsLoadingRuns(false);
        }
    }, [selectedRunId]);

    const fetchTimeline = useCallback(
        async (targetRunId: string) => {
            setIsLoadingTimeline(true);
            try {
                const res = await authFetch(`${SUPERVISOR_URL}/runs/${targetRunId}/timeline`);
                if (!res.ok) {
                    throw new Error('Failed to load run timeline');
                }
                const data = (await res.json()) as RunTimelineResponse;
                setTimeline(data);
            } catch (err) {
                console.error('[RunMap] Failed to fetch timeline:', err);
            } finally {
                setIsLoadingTimeline(false);
            }
        },
        []
    );

    useEffect(() => {
        fetchRuns();
    }, [fetchRuns]);

    useEffect(() => {
        if (!selectedRunId) return;
        fetchTimeline(selectedRunId);
    }, [selectedRunId, fetchTimeline]);

    useEffect(() => {
        if (!isLive) {
            return undefined;
        }
        const interval = window.setInterval(() => {
            fetchRuns();
            if (selectedRunId) {
                fetchTimeline(selectedRunId);
            }
        }, 4000);
        return () => window.clearInterval(interval);
    }, [isLive, fetchRuns, fetchTimeline, selectedRunId]);

    useEffect(() => {
        if (runId && runId !== selectedRunId) {
            setSelectedRunId(runId);
        }
    }, [runId, selectedRunId]);

    const selectedRun = useMemo(() => {
        if (!selectedRunId) return null;
        return runs.find((r) => r.id === selectedRunId) || timeline?.run || null;
    }, [runs, selectedRunId, timeline?.run]);

    const eventTypeCounts = useMemo(() => {
        if (!timeline) return [];
        const counts = new Map<string, number>();
        for (const event of timeline.events) {
            counts.set(event.type, (counts.get(event.type) || 0) + 1);
        }
        return Array.from(counts.entries())
            .map(([type, count]) => ({ type, count }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 12);
    }, [timeline]);

    const handleFollowupSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const trimmed = followup.trim();
        if (!trimmed) return;
        if (!selectedRunId) return;
        sendPrompt(trimmed, { runId: selectedRunId, inputKind: 'followup' });
        setFollowup('');
    };

    return (
        <div className="runmap">
            <div className="runmap-header">
                <div className="runmap-title">RunMap</div>
                <div className="runmap-actions">
                    <button
                        type="button"
                        className="runmap-toggle"
                        onClick={() => setIsLive((prev) => !prev)}
                        title={isLive ? 'Pause live updates' : 'Resume live updates'}
                    >
                        {isLive ? <Pause size={14} /> : <Play size={14} />}
                        {isLive ? 'Pause' : 'Live'}
                    </button>
                    <button
                        type="button"
                        className="runmap-refresh"
                        onClick={() => {
                            fetchRuns();
                            if (selectedRunId) {
                                fetchTimeline(selectedRunId);
                            }
                        }}
                        disabled={isLoadingRuns || isLoadingTimeline}
                    >
                        <RefreshCw size={14} className={isLoadingRuns || isLoadingTimeline ? 'spinning' : ''} />
                        Refresh
                    </button>
                </div>
            </div>

            <div className="runmap-body">
                <aside className="runmap-sidebar">
                    <div className="runmap-sidebar-title">Runs</div>
                    <div className="runmap-runlist">
                        {runs.length === 0 ? (
                            <div className="runmap-empty">No runs yet.</div>
                        ) : (
                            runs.map((run) => (
                                <button
                                    key={run.id}
                                    type="button"
                                    className={`runmap-runitem ${run.id === selectedRunId ? 'active' : ''}`}
                                    onClick={() => setSelectedRunId(run.id)}
                                >
                                    <div className="runmap-runitem-title">
                                        {run.prompt ? run.prompt.slice(0, 80) : run.id}
                                    </div>
                                    <div className="runmap-runitem-meta">
                                        <span className={`status status-${run.status}`}>{run.status}</span>
                                        <span>{formatTime(run.started_at || run.created_at)}</span>
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                </aside>

                <main className="runmap-main">
                    {selectedRun ? (
                        <>
                            <section className="runmap-panel">
                                <div className="runmap-panel-title">Selected Run</div>
                                <div className="runmap-kv">
                                    <div>Run ID</div>
                                    <div className="mono">{selectedRun.id}</div>
                                    <div>Status</div>
                                    <div>{selectedRun.status}</div>
                                    <div>Mode</div>
                                    <div>{selectedRun.mode || '—'}</div>
                                    <div>Started</div>
                                    <div>{formatTime(selectedRun.started_at || selectedRun.created_at)}</div>
                                    <div>Finished</div>
                                    <div>{formatTime(selectedRun.finished_at)}</div>
                                </div>
                            </section>

                            <section className="runmap-panel">
                                <div className="runmap-panel-title">Run Inputs</div>
                                {timeline?.inputs.length ? (
                                    <ul className="runmap-inputs">
                                        {timeline.inputs.map((input) => (
                                            <li key={input.id}>
                                                <span className="pill">{input.kind}</span>
                                                <span>{input.prompt}</span>
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <div className="runmap-empty">No inputs recorded.</div>
                                )}
                            </section>

                            <section className="runmap-panel">
                                <div className="runmap-panel-title">Trace Summary</div>
                                {eventTypeCounts.length ? (
                                    <div className="runmap-events">
                                        {eventTypeCounts.map((item) => (
                                            <div key={item.type} className="runmap-event-card">
                                                <div className="runmap-event-type">{item.type}</div>
                                                <div className="runmap-event-count">{item.count}</div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="runmap-empty">No trace events yet.</div>
                                )}
                            </section>

                            <section className="runmap-panel">
                                <div className="runmap-panel-title">Follow Up</div>
                                <form className="runmap-followup" onSubmit={handleFollowupSubmit}>
                                    <input
                                        type="text"
                                        placeholder="Send a follow-up for this run..."
                                        value={followup}
                                        onChange={(e) => setFollowup(e.target.value)}
                                    />
                                    <button type="submit">Send</button>
                                </form>
                            </section>
                        </>
                    ) : (
                        <div className="runmap-empty large">
                            {isLoadingRuns ? 'Loading runs…' : 'Select a run to view its trace.'}
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
}

