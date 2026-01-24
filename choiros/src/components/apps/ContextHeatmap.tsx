import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Pause, Play, RefreshCw, SlidersHorizontal } from 'lucide-react';
import { authFetch } from '../../lib/auth';
import { useWindowStore } from '../../stores/windows';
import './ContextHeatmap.css';

const API_BASE = import.meta.env.VITE_SUPERVISOR_URL || 'http://localhost:8001';

interface HeatmapNode {
    id: string;
    label: string;
    type: string;
    heat: number;
    event_count: number;
    last_seq: number;
    last_timestamp?: string | null;
    metadata?: Record<string, unknown>;
}

interface HeatmapEdge {
    source: string;
    target: string;
    type: string;
    weight: number;
}

interface HeatmapSnapshot {
    nodes: HeatmapNode[];
    edges: HeatmapEdge[];
    latest_seq: number;
    since_seq: number;
    until_seq: number;
    event_count: number;
}

const RING_RADIUS: Record<string, number> = {
    root: 0,
    run: 120,
    conversation: 150,
    message: 180,
    file: 210,
    tool: 220,
    artifact: 240,
    receipt: 260,
    note: 280,
    event: 300,
};

const TYPE_LABELS: Record<string, string> = {
    root: 'Root',
    run: 'Runs',
    conversation: 'Conversations',
    message: 'Messages',
    file: 'Files',
    tool: 'Tools',
    artifact: 'Artifacts',
    receipt: 'Receipts',
    note: 'Notes',
    event: 'Events',
};

const TYPE_COLORS: Record<string, string> = {
    root: '#4f46e5',
    run: '#06b6d4',
    conversation: '#8b5cf6',
    message: '#14b8a6',
    file: '#10b981',
    tool: '#f59e0b',
    artifact: '#f97316',
    receipt: '#ef4444',
    note: '#ec4899',
    event: '#94a3b8',
};

function buildSnapshotUrl(limit: number, untilSeq?: number | null) {
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    if (untilSeq !== undefined && untilSeq !== null) {
        params.set('until_seq', String(untilSeq));
    }
    return `${API_BASE}/observability/context-heatmap?${params.toString()}`;
}

export function ContextHeatmap() {
    const [snapshot, setSnapshot] = useState<HeatmapSnapshot | null>(null);
    const [isLive, setIsLive] = useState(true);
    const [cursorSeq, setCursorSeq] = useState<number | null>(null);
    const [limit, setLimit] = useState(500);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set(['context-root']));
    const openWindow = useWindowStore((s) => s.openWindow);

    const fetchSnapshot = useCallback(
        async (targetSeq?: number | null) => {
            setIsLoading(true);
            setError(null);
            try {
                const url = buildSnapshotUrl(limit, targetSeq);
                const response = await authFetch(url);
                if (!response.ok) {
                    throw new Error('Failed to load context heatmap');
                }
                const data = (await response.json()) as HeatmapSnapshot;
                setSnapshot(data);
                if (isLive) {
                    setCursorSeq(data.latest_seq);
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load heatmap');
            } finally {
                setIsLoading(false);
            }
        },
        [limit, isLive]
    );

    useEffect(() => {
        fetchSnapshot(isLive ? null : cursorSeq);
    }, [fetchSnapshot, isLive, cursorSeq]);

    useEffect(() => {
        if (!isLive) {
            return undefined;
        }
        const interval = window.setInterval(() => {
            fetchSnapshot(null);
        }, 4000);
        return () => window.clearInterval(interval);
    }, [fetchSnapshot, isLive]);

    useEffect(() => {
        setExpandedNodes((prev) => {
            const next = new Set(prev);
            next.add('context-root');
            return next;
        });
    }, [snapshot?.nodes.length]);

    const nodePositions = useMemo(() => {
        if (!snapshot) {
            return new Map<string, { x: number; y: number }>();
        }
        const positions = new Map<string, { x: number; y: number }>();
        const centerX = 400;
        const centerY = 300;
        const root = snapshot.nodes.find((node) => node.type === 'root') || snapshot.nodes[0];
        if (root) {
            positions.set(root.id, { x: centerX, y: centerY });
        }
        const nodesByRing = new Map<number, HeatmapNode[]>();
        snapshot.nodes
            .filter((node) => node.id !== root?.id)
            .forEach((node) => {
                const radius = RING_RADIUS[node.type] ?? 300;
                const existing = nodesByRing.get(radius) ?? [];
                existing.push(node);
                nodesByRing.set(radius, existing);
            });
        Array.from(nodesByRing.entries()).forEach(([radius, nodes], ringIndex) => {
            const angleStep = (2 * Math.PI) / nodes.length;
            const offset = ringIndex * 0.35;
            nodes.forEach((node, index) => {
                const angle = index * angleStep + offset;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);
                positions.set(node.id, { x, y });
            });
        });
        return positions;
    }, [snapshot]);

    const maxSeq = snapshot?.latest_seq ?? 0;
    const sliderValue = cursorSeq ?? maxSeq;
    const selectedSeq = isLive ? maxSeq : sliderValue;

    const handleReplayChange = (value: number) => {
        setCursorSeq(value);
        setIsLive(false);
        fetchSnapshot(value);
    };

    const nodeCards = snapshot?.nodes
        .filter((node) => node.type !== 'root')
        .sort((a, b) => b.heat - a.heat)
        .slice(0, 8) ?? [];

    const hierarchy = useMemo(() => {
        if (!snapshot) {
            return [];
        }
        const groups = new Map<string, HeatmapNode[]>();
        snapshot.nodes
            .filter((node) => node.type !== 'root')
            .forEach((node) => {
                const group = groups.get(node.type) ?? [];
                group.push(node);
                groups.set(node.type, group);
            });
        return Array.from(groups.entries()).map(([type, nodes]) => ({
            id: `group:${type}`,
            label: TYPE_LABELS[type] ?? type,
            type,
            children: nodes.sort((a, b) => a.label.localeCompare(b.label)),
        }));
    }, [snapshot]);

    const toggleNode = (nodeId: string) => {
        setExpandedNodes((prev) => {
            const next = new Set(prev);
            if (next.has(nodeId)) {
                next.delete(nodeId);
            } else {
                next.add(nodeId);
            }
            return next;
        });
    };

    const handleFileOpen = (node: HeatmapNode) => {
        const filePath = node.metadata?.path as string | undefined;
        if (!filePath) {
            return;
        }
        openWindow('writer', { title: node.label, filePath });
    };

    return (
        <div className="context-heatmap">
            <div className="context-heatmap-header">
                <div className="context-heatmap-title">
                    <SlidersHorizontal size={16} />
                    <span>Context Heatmap</span>
                </div>
                <div className="context-heatmap-actions">
                    <button
                        type="button"
                        className="context-heatmap-toggle"
                        onClick={() => setIsLive((prev) => !prev)}
                    >
                        {isLive ? <Pause size={14} /> : <Play size={14} />}
                        {isLive ? 'Pause' : 'Live'}
                    </button>
                    <button
                        type="button"
                        className="context-heatmap-refresh"
                        onClick={() => fetchSnapshot(isLive ? null : cursorSeq)}
                        disabled={isLoading}
                    >
                        <RefreshCw size={14} className={isLoading ? 'spinning' : ''} />
                        Refresh
                    </button>
                </div>
            </div>

            <div className="context-heatmap-body">
                <div className="context-heatmap-visual">
                    <svg viewBox="0 0 800 600" className="context-heatmap-canvas">
                        {snapshot?.edges.map((edge) => {
                            const source = nodePositions.get(edge.source);
                            const target = nodePositions.get(edge.target);
                            if (!source || !target) {
                                return null;
                            }
                            return (
                                <line
                                    key={`${edge.source}-${edge.target}-${edge.type}`}
                                    x1={source.x}
                                    y1={source.y}
                                    x2={target.x}
                                    y2={target.y}
                                    stroke="rgba(148, 163, 184, 0.35)"
                                    strokeWidth={Math.max(0.6, edge.weight)}
                                />
                            );
                        })}
                        {snapshot?.nodes.map((node) => {
                            const position = nodePositions.get(node.id);
                            if (!position) {
                                return null;
                            }
                            const radius = node.type === 'root' ? 34 : 22;
                            const heat = Math.min(1, Math.max(0.1, node.heat));
                            return (
                                <g key={node.id}>
                                    <circle
                                        cx={position.x}
                                        cy={position.y}
                                        r={radius}
                                        fill={TYPE_COLORS[node.type] ?? '#64748b'}
                                        opacity={heat}
                                    />
                                    <text
                                        x={position.x}
                                        y={position.y}
                                        textAnchor="middle"
                                        dominantBaseline="middle"
                                        fill="#f8fafc"
                                        fontSize={node.type === 'root' ? 12 : 10}
                                        fontWeight={node.type === 'root' ? 600 : 500}
                                    >
                                        {node.label.length > 12 ? `${node.label.slice(0, 12)}…` : node.label}
                                    </text>
                                </g>
                            );
                        })}
                    </svg>
                    {error ? <div className="context-heatmap-error">{error}</div> : null}
                </div>

                <div className="context-heatmap-sidebar">
                    <div className="context-heatmap-section">
                        <div className="context-heatmap-section-title">Replay</div>
                        <div className="context-heatmap-slider">
                            <input
                                type="range"
                                min={0}
                                max={maxSeq}
                                value={selectedSeq}
                                onChange={(event) => handleReplayChange(Number(event.target.value))}
                                disabled={maxSeq === 0}
                            />
                            <div className="context-heatmap-slider-meta">
                                <span>Seq {selectedSeq}</span>
                                <span>{isLive ? 'Live' : 'Replay'}</span>
                            </div>
                        </div>
                        <div className="context-heatmap-meta">
                            <div>Events scanned: {snapshot?.event_count ?? 0}</div>
                            <div>Latest seq: {snapshot?.latest_seq ?? 0}</div>
                        </div>
                    </div>

                    <div className="context-heatmap-section">
                        <div className="context-heatmap-section-title">Top context nodes</div>
                        <div className="context-heatmap-cards">
                            {nodeCards.length === 0 ? (
                                <div className="context-heatmap-empty">No context events yet.</div>
                            ) : (
                                nodeCards.map((node) => (
                                    <div key={node.id} className="context-heatmap-card">
                                        <div className="context-heatmap-card-title">
                                            <span
                                                className="context-heatmap-dot"
                                                style={{ backgroundColor: TYPE_COLORS[node.type] ?? '#64748b' }}
                                            />
                                            {node.label}
                                        </div>
                                        <div className="context-heatmap-card-meta">
                                            <span>{TYPE_LABELS[node.type] ?? node.type}</span>
                                            <span>{Math.round(node.heat * 100)}%</span>
                                            <span>{node.event_count} events</span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <div className="context-heatmap-section">
                        <div className="context-heatmap-section-title">Hierarchy</div>
                        <div className="context-heatmap-tree">
                            <button
                                type="button"
                                className="context-heatmap-tree-node"
                                onClick={() => toggleNode('context-root')}
                            >
                                {expandedNodes.has('context-root') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                <span>Context</span>
                            </button>
                            {expandedNodes.has('context-root') && (
                                <div className="context-heatmap-tree-children">
                                    {hierarchy.map((group) => (
                                        <div key={group.id}>
                                            <button
                                                type="button"
                                                className="context-heatmap-tree-node"
                                                onClick={() => toggleNode(group.id)}
                                            >
                                                {expandedNodes.has(group.id) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                                <span>{group.label}</span>
                                            </button>
                                            {expandedNodes.has(group.id) && (
                                                <div className="context-heatmap-tree-children">
                                                    {group.children.map((node) => (
                                                        <button
                                                            key={node.id}
                                                            type="button"
                                                            className="context-heatmap-tree-leaf"
                                                            onClick={() => {
                                                                if (node.type === 'file') {
                                                                    handleFileOpen(node);
                                                                }
                                                            }}
                                                        >
                                                            <span>{node.label}</span>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="context-heatmap-section">
                        <div className="context-heatmap-section-title">Settings</div>
                        <label className="context-heatmap-input">
                            <span>Event limit</span>
                            <input
                                type="number"
                                min={50}
                                max={2000}
                                value={limit}
                                onChange={(event) => {
                                    const next = Number(event.target.value);
                                    if (Number.isNaN(next)) {
                                        setLimit(500);
                                        return;
                                    }
                                    setLimit(Math.min(2000, Math.max(50, next)));
                                }}
                            />
                        </label>
                    </div>
                </div>
            </div>
        </div>
    );
}
