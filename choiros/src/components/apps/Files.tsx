// Files App - Browse sources and files
import { useEffect, useMemo, useState } from 'react';
import { useSourcesStore } from '../../stores/sources';
import { useWindowStore } from '../../stores/windows';
import {
    ExternalLink,
    Trash2,
    Clock,
    FolderOpen,
    RefreshCw,
    Search,
    ArrowUpDown,
    FileText,
    Folder,
    ArrowUpRight,
} from 'lucide-react';
import './Files.css';

export function Files() {
    const artifacts = useSourcesStore((s) => s.artifacts);
    const isLoading = useSourcesStore((s) => s.isLoading);
    const fetchArtifacts = useSourcesStore((s) => s.fetchArtifacts);
    const deleteArtifact = useSourcesStore((s) => s.deleteArtifact);
    const openWindow = useWindowStore((s) => s.openWindow);
    const [searchQuery, setSearchQuery] = useState('');
    const [sortKey, setSortKey] = useState<'created_at' | 'name' | 'source_type'>(
        'created_at'
    );
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
    const [selectedId, setSelectedId] = useState<string | null>(null);

    useEffect(() => {
        fetchArtifacts();
    }, [fetchArtifacts]);

    useEffect(() => {
        if (selectedId && !artifacts.some((artifact) => artifact.id === selectedId)) {
            setSelectedId(null);
        }
    }, [artifacts, selectedId]);

    const handleOpen = (artifactId: string) => {
        openWindow('writer', { artifactId });
    };

    const handleOpenSelected = () => {
        if (selectedId) {
            handleOpen(selectedId);
        }
    };

    const handleDeleteSelected = () => {
        if (!selectedId) return;
        deleteArtifact(selectedId);
        setSelectedId(null);
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

    const filteredArtifacts = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        const filtered = query
            ? artifacts.filter((artifact) => {
                  const haystack = [
                      artifact.name,
                      artifact.path,
                      artifact.source_url ?? '',
                      artifact.source_type,
                      artifact.mime_type,
                  ]
                      .join(' ')
                      .toLowerCase();
                  return haystack.includes(query);
              })
            : artifacts;

        const sorted = [...filtered].sort((a, b) => {
            if (sortKey === 'name') {
                return a.name.localeCompare(b.name);
            }
            if (sortKey === 'source_type') {
                return a.source_type.localeCompare(b.source_type);
            }
            return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        });

        if (sortDirection === 'desc') {
            sorted.reverse();
        }

        return sorted;
    }, [artifacts, searchQuery, sortDirection, sortKey]);

    const selectedArtifact = useMemo(
        () => artifacts.find((artifact) => artifact.id === selectedId) ?? null,
        [artifacts, selectedId]
    );

    return (
        <div className="files">
            <div className="files-header">
                <div className="files-breadcrumb">
                    <FolderOpen size={16} />
                    <span>/sources</span>
                </div>
                <span className="files-count">
                    {filteredArtifacts.length} of {artifacts.length} items
                </span>
            </div>
            <div className="files-toolbar">
                <div className="files-search">
                    <Search size={14} />
                    <input
                        type="search"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search files, sources, or types"
                        aria-label="Search files"
                    />
                </div>
                <div className="files-toolbar-group">
                    <button
                        className="files-toolbar-button"
                        onClick={() => fetchArtifacts()}
                        title="Refresh"
                    >
                        <RefreshCw size={14} />
                        Refresh
                    </button>
                    <div className="files-sort">
                        <label htmlFor="files-sort">Sort</label>
                        <select
                            id="files-sort"
                            value={sortKey}
                            onChange={(e) =>
                                setSortKey(e.target.value as 'created_at' | 'name' | 'source_type')
                            }
                        >
                            <option value="created_at">Date added</option>
                            <option value="name">Name</option>
                            <option value="source_type">Source</option>
                        </select>
                        <button
                            className="files-toolbar-button"
                            onClick={() =>
                                setSortDirection((dir) => (dir === 'asc' ? 'desc' : 'asc'))
                            }
                            title={`Sort ${sortDirection === 'asc' ? 'descending' : 'ascending'}`}
                        >
                            <ArrowUpDown size={14} />
                        </button>
                    </div>
                    <div className="files-toolbar-actions">
                        <button
                            className="files-toolbar-button"
                            onClick={handleOpenSelected}
                            disabled={!selectedArtifact}
                        >
                            <Folder size={14} />
                            Open
                        </button>
                        {selectedArtifact?.source_url ? (
                            <a
                                className="files-toolbar-button"
                                href={selectedArtifact.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                <ArrowUpRight size={14} />
                                Source
                            </a>
                        ) : (
                            <button className="files-toolbar-button" disabled>
                                <ArrowUpRight size={14} />
                                Source
                            </button>
                        )}
                        <button
                            className="files-toolbar-button danger"
                            onClick={handleDeleteSelected}
                            disabled={!selectedArtifact}
                        >
                            <Trash2 size={14} />
                            Delete
                        </button>
                    </div>
                </div>
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
            ) : filteredArtifacts.length === 0 ? (
                <div className="files-empty">
                    <p>No matches for “{searchQuery}”</p>
                    <p className="files-empty-hint">Try a different search term.</p>
                </div>
            ) : (
                <div className="files-list">
                    {filteredArtifacts.map((artifact) => (
                        <div
                            key={artifact.id}
                            className={`file-item${
                                selectedId === artifact.id ? ' is-selected' : ''
                            }`}
                            onDoubleClick={() => handleOpen(artifact.id)}
                            onClick={() => setSelectedId(artifact.id)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(event) => {
                                if (event.key === 'Enter') {
                                    handleOpen(artifact.id);
                                }
                            }}
                        >
                            <span className="file-icon">
                                {getSourceIcon(artifact.source_type)}
                            </span>
                            <div className="file-info">
                                <span className="file-name">{artifact.name}</span>
                                <span className="file-meta">
                                    <Clock size={12} />
                                    {formatDate(artifact.created_at)}
                                    <span className="file-meta-divider">•</span>
                                    <FileText size={12} />
                                    {artifact.mime_type || 'Unknown type'}
                                    <span className="file-meta-divider">•</span>
                                    {artifact.source_type}
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
