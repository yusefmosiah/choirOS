// Files App - Browse sources and files
import { useEffect } from 'react';
import { useSourcesStore } from '../../stores/sources';
import { useWindowStore } from '../../stores/windows';
import { ExternalLink, Trash2, Clock, FolderOpen } from 'lucide-react';
import './Files.css';

export function Files() {
    const artifacts = useSourcesStore((s) => s.artifacts);
    const isLoading = useSourcesStore((s) => s.isLoading);
    const fetchArtifacts = useSourcesStore((s) => s.fetchArtifacts);
    const deleteArtifact = useSourcesStore((s) => s.deleteArtifact);
    const openWindow = useWindowStore((s) => s.openWindow);

    useEffect(() => {
        fetchArtifacts();
    }, [fetchArtifacts]);

    const handleOpen = (artifactId: string) => {
        openWindow('writer', { artifactId });
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getSourceIcon = (sourceType: string) => {
        switch (sourceType) {
            case 'youtube':
                return '🎬';
            case 'web':
                return '🌐';
            case 'upload':
                return '📄';
            default:
                return '📁';
        }
    };

    return (
        <div className="files">
            <div className="files-header">
                <div className="files-breadcrumb">
                    <FolderOpen size={16} />
                    <span>/sources</span>
                </div>
                <span className="files-count">{artifacts.length} items</span>
            </div>

            {isLoading ? (
                <div className="files-loading">Loading...</div>
            ) : artifacts.length === 0 ? (
                <div className="files-empty">
                    <p>No files yet</p>
                    <p className="files-empty-hint">
                        Paste a URL in the ? bar or click ? → Upload Files
                    </p>
                </div>
            ) : (
                <div className="files-list">
                    {artifacts.map((artifact) => (
                        <div
                            key={artifact.id}
                            className="file-item"
                            onDoubleClick={() => handleOpen(artifact.id)}
                        >
                            <span className="file-icon">
                                {getSourceIcon(artifact.source_type)}
                            </span>
                            <div className="file-info">
                                <span className="file-name">{artifact.name}</span>
                                <span className="file-meta">
                                    <Clock size={12} />
                                    {formatDate(artifact.created_at)}
                                </span>
                            </div>
                            <div className="file-actions">
                                {artifact.source_url && (
                                    <a
                                        href={artifact.source_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="file-link"
                                        onClick={(e) => e.stopPropagation()}
                                        title="Open source URL"
                                    >
                                        <ExternalLink size={14} />
                                    </a>
                                )}
                                <button
                                    className="file-delete"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        deleteArtifact(artifact.id);
                                    }}
                                    title="Delete"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
