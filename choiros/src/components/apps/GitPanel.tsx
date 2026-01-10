// GitPanel App - Version Control UI
import { useEffect, useState, useCallback } from 'react';
import { GitBranch, GitCommit, RotateCcw, Save, RefreshCw, AlertCircle, Check, Clock } from 'lucide-react';
import './GitPanel.css';

interface GitStatus {
    modified: string[];
    added: string[];
    deleted: string[];
    untracked: string[];
    clean: boolean;
}

interface Commit {
    sha: string;
    message: string;
    date: string;
    author: string;
}

interface GitState {
    head: string | null;
    status: GitStatus | null;
    commits: Commit[];
    isLoading: boolean;
    error: string | null;
}

const API_BASE = 'http://localhost:8001';

export function GitPanel() {
    const [state, setState] = useState<GitState>({
        head: null,
        status: null,
        commits: [],
        isLoading: true,
        error: null,
    });
    const [checkpointMessage, setCheckpointMessage] = useState('');
    const [isCheckpointing, setIsCheckpointing] = useState(false);
    const [isReverting, setIsReverting] = useState<string | null>(null);

    const fetchGitState = useCallback(async () => {
        setState(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            const [statusRes, logRes] = await Promise.all([
                fetch(`${API_BASE}/git/status`),
                fetch(`${API_BASE}/git/log?count=10`),
            ]);

            if (!statusRes.ok || !logRes.ok) {
                throw new Error('Failed to fetch git state');
            }

            const statusData = await statusRes.json();
            const logData = await logRes.json();

            setState({
                head: statusData.head,
                status: statusData.status,
                commits: logData.commits,
                isLoading: false,
                error: null,
            });
        } catch (err) {
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: err instanceof Error ? err.message : 'Unknown error',
            }));
        }
    }, []);

    useEffect(() => {
        fetchGitState();
    }, [fetchGitState]);

    const handleCheckpoint = async () => {
        setIsCheckpointing(true);
        try {
            const res = await fetch(`${API_BASE}/git/checkpoint`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: checkpointMessage || null }),
            });

            const data = await res.json();

            if (data.success) {
                setCheckpointMessage('');
                await fetchGitState();
            } else {
                setState(prev => ({ ...prev, error: data.error || 'Checkpoint failed' }));
            }
        } catch (err) {
            setState(prev => ({
                ...prev,
                error: err instanceof Error ? err.message : 'Checkpoint failed',
            }));
        } finally {
            setIsCheckpointing(false);
        }
    };

    const handleRevert = async (sha: string) => {
        if (!confirm(`Revert to commit ${sha}? This will discard all changes after this commit.`)) {
            return;
        }

        setIsReverting(sha);
        try {
            const res = await fetch(`${API_BASE}/git/revert`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sha }),
            });

            const data = await res.json();

            if (data.success) {
                await fetchGitState();
            } else {
                setState(prev => ({ ...prev, error: data.error || 'Revert failed' }));
            }
        } catch (err) {
            setState(prev => ({
                ...prev,
                error: err instanceof Error ? err.message : 'Revert failed',
            }));
        } finally {
            setIsReverting(null);
        }
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

    const totalChanges = state.status
        ? state.status.modified.length +
        state.status.added.length +
        state.status.deleted.length +
        state.status.untracked.length
        : 0;

    return (
        <div className="git-panel">
            {/* Header */}
            <div className="git-header">
                <div className="git-head">
                    <GitBranch size={16} />
                    <span className="git-head-sha">{state.head || '---'}</span>
                </div>
                <button
                    className="git-refresh"
                    onClick={fetchGitState}
                    disabled={state.isLoading}
                    title="Refresh"
                >
                    <RefreshCw size={14} className={state.isLoading ? 'spinning' : ''} />
                </button>
            </div>

            {/* Error display */}
            {state.error && (
                <div className="git-error">
                    <AlertCircle size={14} />
                    <span>{state.error}</span>
                </div>
            )}

            {/* Status section */}
            <div className="git-section">
                <div className="git-section-header">
                    <span>Working Tree</span>
                    {state.status?.clean ? (
                        <span className="git-status-badge clean">
                            <Check size={12} /> Clean
                        </span>
                    ) : (
                        <span className="git-status-badge changes">
                            {totalChanges} changes
                        </span>
                    )}
                </div>

                {state.status && !state.status.clean && (
                    <div className="git-changes">
                        {state.status.modified.map(f => (
                            <div key={f} className="git-change modified">
                                <span className="git-change-type">M</span>
                                <span className="git-change-path">{f}</span>
                            </div>
                        ))}
                        {state.status.added.map(f => (
                            <div key={f} className="git-change added">
                                <span className="git-change-type">A</span>
                                <span className="git-change-path">{f}</span>
                            </div>
                        ))}
                        {state.status.deleted.map(f => (
                            <div key={f} className="git-change deleted">
                                <span className="git-change-type">D</span>
                                <span className="git-change-path">{f}</span>
                            </div>
                        ))}
                        {state.status.untracked.map(f => (
                            <div key={f} className="git-change untracked">
                                <span className="git-change-type">?</span>
                                <span className="git-change-path">{f}</span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Checkpoint input */}
                <div className="git-checkpoint">
                    <input
                        type="text"
                        placeholder="Checkpoint message (optional)"
                        value={checkpointMessage}
                        onChange={(e) => setCheckpointMessage(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleCheckpoint()}
                        disabled={isCheckpointing}
                    />
                    <button
                        onClick={handleCheckpoint}
                        disabled={isCheckpointing || state.status?.clean}
                        title={state.status?.clean ? 'Nothing to commit' : 'Save checkpoint'}
                    >
                        <Save size={14} />
                        {isCheckpointing ? 'Saving...' : 'Checkpoint'}
                    </button>
                </div>
            </div>

            {/* Commit history */}
            <div className="git-section">
                <div className="git-section-header">
                    <span>History</span>
                </div>
                <div className="git-commits">
                    {state.commits.map((commit, idx) => (
                        <div
                            key={commit.sha}
                            className={`git-commit ${idx === 0 ? 'current' : ''}`}
                        >
                            <div className="git-commit-icon">
                                <GitCommit size={14} />
                            </div>
                            <div className="git-commit-info">
                                <div className="git-commit-message">{commit.message}</div>
                                <div className="git-commit-meta">
                                    <span className="git-commit-sha">{commit.sha.slice(0, 8)}</span>
                                    <span className="git-commit-date">
                                        <Clock size={10} />
                                        {formatDate(commit.date)}
                                    </span>
                                </div>
                            </div>
                            {idx > 0 && (
                                <button
                                    className="git-commit-revert"
                                    onClick={() => handleRevert(commit.sha)}
                                    disabled={isReverting === commit.sha}
                                    title="Revert to this commit"
                                >
                                    <RotateCcw size={12} />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
