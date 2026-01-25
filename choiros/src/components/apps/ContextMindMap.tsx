import { useEffect, useState, useMemo, useCallback } from 'react';
import { authFetch } from '../../lib/auth';
import './ContextMindMap.css';

const SUPERVISOR_URL = import.meta.env.VITE_SUPERVISOR_URL || 'http://localhost:8001';

interface HeatmapNode {
    id: string;
    label: string;
    type: string;
    heat: number;
    event_count: number;
    last_seq: number;
    last_timestamp: string | null;
    metadata: Record<string, unknown>;
}

interface HeatmapEdge {
    source: string;
    target: string;
    type: string;
    weight: number;
}

interface HeatmapResponse {
    nodes: HeatmapNode[];
    edges: HeatmapEdge[];
    latest_seq: number;
    since_seq: number;
    until_seq: number;
    event_count: number;
}

interface VisualNode {
    id: string;
    x: number;
    y: number;
    label: string;
    type: string;
    color: string;
    radius: number;
    heat: number;
}

interface VisualLink {
    source: VisualNode;
    target: VisualNode;
    weight: number;
}

const TYPE_COLORS: Record<string, string> = {
    root: '#8b5cf6',
    file: '#f87171',
    tool: '#60a5fa',
    message: '#4ade80',
    conversation: '#c084fc',
    note: '#fcd34d',
};

export function ContextMindMap() {
    const [data, setData] = useState<HeatmapResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await authFetch(`${SUPERVISOR_URL}/observability/context-heatmap?limit=500`);
            if (res.ok) {
                const json = await res.json();
                setData(json);
            } else {
                setError(`Failed to fetch: ${res.status}`);
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const { nodes: visualNodes, links: visualLinks } = useMemo(() => {
        if (!data || data.nodes.length === 0) return { nodes: [], links: [] };

        const width = 900;
        const height = 700;
        const cx = width / 2;
        const cy = height / 2;

        const nodeMap = new Map<string, HeatmapNode>();
        data.nodes.forEach(n => nodeMap.set(n.id, n));

        const adjacency = new Map<string, Set<string>>();
        data.edges.forEach(e => {
            if (!adjacency.has(e.source)) adjacency.set(e.source, new Set());
            if (!adjacency.has(e.target)) adjacency.set(e.target, new Set());
            adjacency.get(e.source)!.add(e.target);
            adjacency.get(e.target)!.add(e.source);
        });

        const rootNode = data.nodes.find(n => n.type === 'root');
        const rootId = rootNode?.id || 'context-root';

        const positioned = new Map<string, VisualNode>();
        const maxHeat = Math.max(...data.nodes.map(n => n.heat), 1);

        if (rootNode) {
            positioned.set(rootId, {
                id: rootId,
                x: cx,
                y: cy,
                label: rootNode.label,
                type: rootNode.type,
                color: TYPE_COLORS[rootNode.type] || '#888',
                radius: 40,
                heat: rootNode.heat,
            });
        }

        const firstLevel = data.nodes.filter(n => n.type !== 'root' && adjacency.get(rootId)?.has(n.id));
        const firstLevelRadius = 180;
        firstLevel.forEach((node, i) => {
            const angle = (i / firstLevel.length) * 2 * Math.PI - Math.PI / 2;
            const heat = node.heat / maxHeat;
            positioned.set(node.id, {
                id: node.id,
                x: cx + firstLevelRadius * Math.cos(angle),
                y: cy + firstLevelRadius * Math.sin(angle),
                label: node.label.length > 20 ? node.label.slice(0, 17) + '...' : node.label,
                type: node.type,
                color: TYPE_COLORS[node.type] || '#888',
                radius: 15 + heat * 15,
                heat: node.heat,
            });
        });

        const remaining = data.nodes.filter(n => !positioned.has(n.id));
        const secondLevelRadius = 320;
        remaining.forEach((node, i) => {
            const angle = (i / Math.max(remaining.length, 1)) * 2 * Math.PI - Math.PI / 4;
            const heat = node.heat / maxHeat;
            positioned.set(node.id, {
                id: node.id,
                x: cx + secondLevelRadius * Math.cos(angle),
                y: cy + secondLevelRadius * Math.sin(angle),
                label: node.label.length > 15 ? node.label.slice(0, 12) + '...' : node.label,
                type: node.type,
                color: TYPE_COLORS[node.type] || '#888',
                radius: 12 + heat * 10,
                heat: node.heat,
            });
        });

        const visualLinks: VisualLink[] = [];
        data.edges.forEach(e => {
            const src = positioned.get(e.source);
            const tgt = positioned.get(e.target);
            if (src && tgt) {
                visualLinks.push({ source: src, target: tgt, weight: e.weight });
            }
        });

        return { nodes: Array.from(positioned.values()), links: visualLinks };
    }, [data]);

    if (loading && !data) {
        return <div className="mindmap-container loading">Loading Context Mind Map...</div>;
    }

    if (error) {
        return (
            <div className="mindmap-container empty">
                <p>Error: {error}</p>
                <button onClick={fetchData} className="mindmap-refresh">Retry</button>
            </div>
        );
    }

    if (!data || visualNodes.length === 0) {
        return <div className="mindmap-container empty">No context data available.</div>;
    }

    return (
        <div className="mindmap-container">
            <button onClick={fetchData} disabled={loading} className="mindmap-refresh">
                {loading ? 'Refreshing...' : 'Refresh'}
            </button>
            <div className="mindmap-svg-container">
                <svg width="100%" height="100%" viewBox="0 0 900 700" preserveAspectRatio="xMidYMid meet">
                    <g>
                        {visualLinks.map((link, i) => (
                            <line
                                key={i}
                                x1={link.source.x}
                                y1={link.source.y}
                                x2={link.target.x}
                                y2={link.target.y}
                                className="link"
                                stroke="#555"
                                strokeWidth={1 + link.weight}
                                opacity={0.4 + link.weight * 0.2}
                            />
                        ))}
                        {visualNodes.map((node) => (
                            <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
                                <circle
                                    r={node.radius}
                                    className={`node-circle ${node.type}`}
                                    style={{ stroke: node.color, fill: `${node.color}33` }}
                                />
                                <text
                                    dy={node.radius + 14}
                                    className={`node-text ${node.type}`}
                                    textAnchor="middle"
                                >
                                    {node.label}
                                </text>
                                <title>{`${node.label}\nType: ${node.type}\nHeat: ${node.heat.toFixed(2)}`}</title>
                            </g>
                        ))}
                    </g>
                </svg>
            </div>
            <div className="mindmap-controls">
                <div className="mindmap-info">
                    <span>Events: {data.event_count}</span>
                    <span>Nodes: {data.nodes.length}</span>
                    <span>Seq: {data.since_seq} → {data.until_seq}</span>
                </div>
            </div>
        </div>
    );
}
