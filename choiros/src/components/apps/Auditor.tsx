
import { useEffect, useState } from 'react';
import { AlertTriangle, Lightbulb, Search, StopCircle } from 'lucide-react';
import './Auditor.css';

interface AuditEvent {
    seq: number;
    timestamp: string;
    type: string;
    payload: {
        path: string;
        mood: string;
        critique: string;
        blind_spots?: string[];
        citations?: string[];
    };
}

export function Auditor() {
    const [audits, setAudits] = useState<AuditEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedAudit, setSelectedAudit] = useState<AuditEvent | null>(null);

    const fetchAudits = async () => {
        try {
            const res = await fetch('http://localhost:8001/agent/audits?limit=50');
            const data = await res.json();
            setAudits(data.audits || []);
            setLoading(false);
        } catch (e) {
            console.error(e);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAudits();
        const interval = setInterval(fetchAudits, 5000);
        return () => clearInterval(interval);
    }, []);

    const getMoodColor = (mood: string) => {
        const m = mood.toLowerCase();
        if (m.includes('sharp') || m.includes('alarmed') || m.includes('critical')) return 'var(--color-audit-critical)';
        if (m.includes('concerned') || m.includes('skeptical')) return 'var(--color-audit-warning)';
        return 'var(--color-audit-info)';
    };

    return (
        <div className="auditor-app">
            <div className="auditor-sidebar">
                <div className="auditor-header">
                    <h2>Recent Audits</h2>
                    <span className="badge">{audits.length}</span>
                </div>
                <div className="audit-list">
                    {loading && <div className="loading">Loading audits...</div>}
                    {audits.map((audit) => (
                        <div
                            key={audit.seq}
                            className={`audit-item ${selectedAudit?.seq === audit.seq ? 'active' : ''}`}
                            onClick={() => setSelectedAudit(audit)}
                            style={{ borderLeftColor: getMoodColor(audit.payload.mood) }}
                        >
                            <div className="audit-item-header">
                                <span className="audit-path" title={audit.payload.path}>
                                    {audit.payload.path.split('/').pop()}
                                </span>
                                <span className="audit-time">
                                    {new Date(audit.timestamp).toLocaleTimeString()}
                                </span>
                            </div>
                            <div className="audit-mood" style={{ color: getMoodColor(audit.payload.mood) }}>
                                {audit.payload.mood}
                            </div>
                            <div className="audit-snippet">
                                {audit.payload.critique.slice(0, 60)}...
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="auditor-detail">
                {selectedAudit ? (
                    <div className="detail-content">
                        <div className="detail-header">
                            <h3>{selectedAudit.payload.path}</h3>
                            <span
                                className="mood-badge"
                                style={{
                                    backgroundColor: getMoodColor(selectedAudit.payload.mood),
                                    color: '#fff'
                                }}
                            >
                                {selectedAudit.payload.mood}
                            </span>
                        </div>

                        <div className="critique-section">
                            <h4><AlertTriangle size={18} /> Critique</h4>
                            <p className="critique-text">{selectedAudit.payload.critique}</p>
                        </div>

                        {selectedAudit.payload.blind_spots && selectedAudit.payload.blind_spots.length > 0 && (
                            <div className="critique-section">
                                <h4><Lightbulb size={18} /> Blind Spots</h4>
                                <ul>
                                    {selectedAudit.payload.blind_spots.map((bs, i) => (
                                        <li key={i}>{bs}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {selectedAudit.payload.citations && selectedAudit.payload.citations.length > 0 && (
                            <div className="critique-section">
                                <h4><Search size={18} /> Citations</h4>
                                <ul className="citations-list">
                                    {selectedAudit.payload.citations.map((c, i) => (
                                        <li key={i}>{c}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="empty-state">
                        <StopCircle size={48} opacity={0.2} />
                        <p>Select an audit to view details</p>
                    </div>
                )}
            </div>
        </div>
    );
}
