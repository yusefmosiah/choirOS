import { useEffect, useState, useMemo } from 'react';
import { authFetch } from '../../lib/auth';
import './ContextMindMap.css';

const SUPERVISOR_URL = import.meta.env.VITE_SUPERVISOR_URL || 'http://localhost:8001';

interface ContextFootprint {
    conversation_id: string | number;
    mode: string;
    ahdb_state: Record<string, unknown>;
    recent_files: string[];
    recent_messages: { role: string; content: string; timestamp: string }[];
    timestamp: string;
}

interface ContextEvent {
    seq: number;
    timestamp: string;
    payload: ContextFootprint;
}

interface Node {
    id: string;
    x: number;
    y: number;
    label: string;
    type: 'root' | 'category' | 'ahdb' | 'file' | 'message';
    data?: unknown;
    parent?: Node;
    angle?: number; // For radial layout
    color?: string;
}

interface Link {
    source: Node;
    target: Node;
}

export function ContextMindMap() {
    const [history, setHistory] = useState<ContextEvent[]>([]);
    const [currentIndex, setCurrentIndex] = useState<number>(0);
    const [loading, setLoading] = useState(false);

    // Fetch history
    useEffect(() => {
        const fetchHistory = async () => {
            setLoading(true);
            try {
                const res = await authFetch(`${SUPERVISOR_URL}/context/history?limit=1000`);
                if (res.ok) {
                    const data = await res.json();
                    const events = data.history as ContextEvent[];
                    setHistory(events);
                    if (events.length > 0) {
                        setCurrentIndex(events.length - 1);
                    }
                }
            } catch (e) {
                console.error("Failed to fetch context history", e);
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, []);

    const currentEvent = history[currentIndex];

    // Compute layout (Radial Tree)
    const { nodes, links } = useMemo(() => {
        if (!currentEvent) return { nodes: [], links: [] };

        const { mode, ahdb_state, recent_files, recent_messages } = currentEvent.payload;
        const width = 900;
        const height = 700;
        const cx = width / 2;
        const cy = height / 2;

        const nodes: Node[] = [];
        const links: Link[] = [];

        // Root Node
        const rootNode: Node = {
            id: 'root',
            x: cx,
            y: cy,
            label: mode || 'Context',
            type: 'root'
        };
        nodes.push(rootNode);

        // Categories
        const categories = [
            { id: 'cat-ahdb', label: 'AHDB', type: 'category' as const, color: '#fcd34d' },
            { id: 'cat-files', label: 'Files', type: 'category' as const, color: '#f87171' },
            { id: 'cat-chat', label: 'Chat', type: 'category' as const, color: '#4ade80' },
        ];

        // Assign angles to categories (0, 120, 240 degrees)
        const catRadius = 150;

        categories.forEach((cat, i) => {
            const angle = (i / categories.length) * 2 * Math.PI - Math.PI / 2;
            const node: Node = {
                id: cat.id,
                x: cx + catRadius * Math.cos(angle),
                y: cy + catRadius * Math.sin(angle),
                label: cat.label,
                type: 'category',
                angle: angle,
                color: cat.color
            };
            nodes.push(node);
            links.push({ source: rootNode, target: node });

            // Add Children
            let items: { id: string, label: string, type: 'ahdb'|'file'|'message', data?: any }[] = [];

            if (cat.id === 'cat-ahdb') {
                items = Object.entries(ahdb_state || {}).map(([k, v]) => ({
                    id: `ahdb-${k}`,
                    label: k,
                    type: 'ahdb',
                    data: v
                }));
            } else if (cat.id === 'cat-files') {
                items = (recent_files || []).map(f => ({
                    id: `file-${f}`,
                    label: f.split('/').pop() || f,
                    type: 'file',
                    data: f
                }));
            } else if (cat.id === 'cat-chat') {
                items = (recent_messages || []).map((m, idx) => ({
                    id: `msg-${idx}`,
                    label: `${m.role}: ${m.content.slice(0, 20)}...`,
                    type: 'message',
                    data: m.content
                }));
            }

            // Distribute items in a fan around the category
            const itemRadius = 120; // relative to category node? No, better relative to root or accumulated
            // Let's do 2-level radial.
            // Items are placed around the category node, but pointing outwards.

            const spread = Math.PI / 2; // 90 degrees spread
            const startAngle = node.angle! - spread / 2;

            items.forEach((item, j) => {
                const itemAngle = startAngle + (j / Math.max(1, items.length - 1)) * spread;
                // Position relative to category node? Or absolute?
                // Let's go further out from center passing through category.
                const dist = catRadius + 140;

                // Correction: spread items around the category node's vector
                const finalAngle = node.angle! + (j - (items.length-1)/2) * (Math.PI/6); // ~30 deg per item

                const itemNode: Node = {
                    id: item.id,
                    x: cx + dist * Math.cos(finalAngle),
                    y: cy + dist * Math.sin(finalAngle),
                    label: item.label,
                    type: item.type,
                    data: item.data,
                    color: cat.color // Inherit color
                };
                nodes.push(itemNode);
                links.push({ source: node, target: itemNode });
            });
        });

        return { nodes, links };
    }, [currentEvent]);

    const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setCurrentIndex(Number(e.target.value));
    };

    if (loading && history.length === 0) {
        return <div className="mindmap-container loading">Loading Context History...</div>;
    }

    if (!currentEvent) {
        return <div className="mindmap-container empty">No context history available.</div>;
    }

    return (
        <div className="mindmap-container">
            <div className="mindmap-svg-container">
                <svg width="100%" height="100%" viewBox="0 0 900 700" preserveAspectRatio="xMidYMid meet">
                    <defs>
                        <marker id="arrow" markerWidth="10" markerHeight="10" refX="20" refY="3" orient="auto" markerUnits="strokeWidth">
                            <path d="M0,0 L0,6 L9,3 z" fill="#555" />
                        </marker>
                    </defs>
                    <g>
                        {links.map((link, i) => (
                            <line
                                key={i}
                                x1={link.source.x}
                                y1={link.source.y}
                                x2={link.target.x}
                                y2={link.target.y}
                                className="link"
                                stroke="#555"
                                strokeWidth="2"
                                opacity="0.6"
                            />
                        ))}
                        {nodes.map((node) => (
                            <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
                                <circle
                                    r={node.type === 'root' ? 40 : node.type === 'category' ? 30 : 20}
                                    className={`node-circle ${node.type}`}
                                    style={node.color ? { stroke: node.color } : undefined}
                                />
                                <text
                                    dy={node.type === 'root' ? 5 : 40}
                                    className={`node-text ${node.type}`}
                                    textAnchor="middle"
                                >
                                    {node.label}
                                </text>
                                {node.data && <title>{typeof node.data === 'string' ? node.data : JSON.stringify(node.data, null, 2)}</title>}
                            </g>
                        ))}
                    </g>
                </svg>
            </div>
            <div className="mindmap-controls">
                <input
                    type="range"
                    min="0"
                    max={Math.max(0, history.length - 1)}
                    value={currentIndex}
                    onChange={handleSliderChange}
                    className="mindmap-slider"
                />
                <div className="mindmap-info">
                    <span className="timestamp">{new Date(currentEvent.timestamp || Date.now()).toLocaleTimeString()}</span>
                    <span className="seq">Seq: {currentEvent.seq}</span>
                    <span className="mode">Mode: {currentEvent.payload.mode}</span>
                </div>
            </div>
        </div>
    );
}
