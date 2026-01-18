// Taskbar Component
import { useState, useRef, type FormEvent } from 'react';
import { useWindowStore } from '../../stores/windows';
import { useSourcesStore } from '../../stores/sources';
import { APP_REGISTRY } from '../../lib/apps';
import { isUrl, createArtifact, type ParseMode } from '../../lib/api';
import { useAgent, type AgentMessage } from '../../hooks/useAgent';
import { Upload, Link, Loader2, AlertCircle, Wifi, WifiOff, KeyRound } from 'lucide-react';
import { useEventStore } from '../../stores/events';
import './Taskbar.css';

// Duplicate confirmation state
interface DuplicateConfirm {
    url: string;
    existingName: string;
    existingId: string;
}

export function Taskbar() {
    const [input, setInput] = useState('');
    const [showMenu, setShowMenu] = useState(false);
    const [duplicateConfirm, setDuplicateConfirm] = useState<DuplicateConfirm | null>(null);
    
    // Use centralized event store
    const addEvent = useEventStore((s) => s.addEvent);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Track agent response for saving as artifact
    const agentResponseRef = useRef<{ prompt: string; messages: string[] }>({ prompt: '', messages: [] });

    const windows = useWindowStore((s) => s.windows);
    const focusWindow = useWindowStore((s) => s.focusWindow);
    const restoreWindow = useWindowStore((s) => s.restoreWindow);
    const openWindow = useWindowStore((s) => s.openWindow);

    const parseUrlAndCreate = useSourcesStore((s) => s.parseUrlAndCreate);
    const checkUrlExists = useSourcesStore((s) => s.checkUrlExists);
    const uploadAndParse = useSourcesStore((s) => s.uploadAndParse);
    const isParsingUrl = useSourcesStore((s) => s.isParsingUrl);
    const isUploading = useSourcesStore((s) => s.isUploading);
    const error = useSourcesStore((s) => s.error);
    const clearError = useSourcesStore((s) => s.clearError);
    const fetchArtifacts = useSourcesStore((s) => s.fetchArtifacts);

    // Agent WebSocket connection
    const { sendPrompt, isProcessing: isAgentProcessing, isConnected: isAgentConnected } = useAgent({
        onMessage: async (message: AgentMessage) => {
            if (message.type === 'text' && typeof message.content === 'string') {
                // Accumulate text messages
                agentResponseRef.current.messages.push(message.content);
                showToast(message.content.slice(0, 80) + '...', 'info');
            } else if (message.type === 'tool_use' && typeof message.content === 'object') {
                const tool = (message.content as { tool?: string })?.tool || 'tool';
                showToast(`Using ${tool}...`, 'info');
            } else if (message.type === 'error') {
                showToast(String(message.content), 'error');
            } else if (message.type === 'done') {
                // Save accumulated response as artifact
                const { prompt, messages } = agentResponseRef.current;
                if (messages.length > 0) {
                    try {
                        const name = `Agent: ${prompt.slice(0, 40)}${prompt.length > 40 ? '...' : ''}`;
                        const content = `# ${prompt}\n\n${messages.join('\n\n')}`;
                        const result = await createArtifact({ name, content, source_type: 'agent' });
                        await fetchArtifacts(); // Refresh artifact list
                        showToast(`Saved: ${result.name}`, 'success', result.artifact_id);
                    } catch (e) {
                        showToast('Agent done (failed to save)', 'error');
                    }
                } else {
                    showToast('Agent completed', 'success');
                }
                // Reset for next prompt
                agentResponseRef.current = { prompt: '', messages: [] };
            }
        },
    });

    const showToast = (message: string, type: 'info' | 'success' | 'error' | 'thinking' = 'info', artifactId?: string) => {
        addEvent(message, type, artifactId);
    };


    const parseWithMode = async (url: string, mode: ParseMode) => {
        showToast('Parsing URL...', 'info');
        const result = await parseUrlAndCreate(url, mode);
        if (result) {
            showToast(`Source added: ${result.name}`, 'success', result.artifact_id);
        } else {
            showToast(error || 'Failed to parse URL', 'error');
            clearError();
        }
    };

    const handleDuplicateChoice = async (choice: 'cancel' | 'overwrite' | 'keep_both') => {
        if (!duplicateConfirm) return;

        const { url } = duplicateConfirm;
        setDuplicateConfirm(null);

        if (choice === 'cancel') {
            showToast('Cancelled', 'info');
            return;
        }

        await parseWithMode(url, choice);
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        const trimmedInput = input.trim();

        // Check if it's a URL
        if (isUrl(trimmedInput)) {
            setInput('');

            // First, check if URL already exists
            try {
                const check = await checkUrlExists(trimmedInput);
                if (check.exists && check.artifact_id && check.name) {
                    // Show duplicate confirmation
                    setDuplicateConfirm({
                        url: trimmedInput,
                        existingName: check.name,
                        existingId: check.artifact_id,
                    });
                    return;
                }
            } catch {
                // If check fails, continue with parse anyway
            }

            // No duplicate, proceed with parsing
            await parseWithMode(trimmedInput, 'create');
            return;
        }

        // Send to agent
        if (isAgentConnected) {
            // Capture prompt for artifact naming
            agentResponseRef.current = { prompt: trimmedInput, messages: [] };
            sendPrompt(trimmedInput);
            setInput('');
            showToast('Sending to agent...', 'info');
        } else {
            showToast('Agent not connected', 'error');
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setShowMenu(false);
        showToast(`Parsing ${file.name}...`, 'info');

        const result = await uploadAndParse(file);
        if (result) {
            showToast(`Source added: ${result.name}`, 'success', result.artifact_id);
        } else {
            showToast(error || 'Failed to parse file', 'error');
            clearError();
        }

        // Reset file input
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const runningWindows = Array.from(windows.values());
    const isLoading = isParsingUrl || isUploading || isAgentProcessing;

    return (
        <div className="taskbar">
            <div className="taskbar-menu-container">
                <button
                    className={`taskbar-menu-btn ${showMenu ? 'active' : ''}`}
                    type="button"
                    title="Command Menu"
                    onClick={() => setShowMenu(!showMenu)}
                >
                    ?
                </button>

                {showMenu && (
                    <div className="taskbar-menu">
                        <button
                            className="taskbar-menu-item"
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <Upload size={16} />
                            Upload Files
                        </button>
                        <button
                            className="taskbar-menu-item"
                            onClick={() => {
                                openWindow('auth');
                                setShowMenu(false);
                            }}
                        >
                            <KeyRound size={16} />
                            Passkeys & Sessions
                        </button>
                        <div className="taskbar-menu-divider" />
                        <div className="taskbar-menu-hint">
                            <Link size={14} />
                            Paste URL in search bar to parse
                        </div>
                    </div>
                )}

                <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden-file-input"
                    onChange={handleFileUpload}
                    accept=".pdf,.docx,.doc,.pptx,.ppt,.xlsx,.xls,.txt,.md,.json,.csv,.html,.htm"
                />
            </div>

            <form className="taskbar-input-form" onSubmit={handleSubmit}>
                <input
                    type="text"
                    className="taskbar-input"
                    placeholder={isLoading ? 'Parsing...' : 'Ask anything, paste URL, or type ? for commands...'}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isLoading}
                />
                {isLoading && (
                    <div className="taskbar-input-loader">
                        <Loader2 size={16} className="spin" />
                    </div>
                )}
            </form>

            {/* Agent connection indicator */}
            <div
                className={`taskbar-agent-status ${isAgentConnected ? 'connected' : 'disconnected'}`}
                title={isAgentConnected ? 'Agent connected' : 'Agent disconnected'}
            >
                {isAgentConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
            </div>

            <div className="taskbar-tray">
                {runningWindows.map((win) => {
                    const app = APP_REGISTRY[win.appId];
                    const IconComponent = app?.icon;

                    return (
                        <button
                            key={win.id}
                            className={`taskbar-app ${win.isFocused ? 'focused' : ''} ${win.isMinimized ? 'minimized' : ''}`}
                            onClick={() => win.isMinimized ? restoreWindow(win.id) : focusWindow(win.id)}
                            title={win.title}
                            type="button"
                        >
                            {IconComponent && <IconComponent size={18} />}
                        </button>
                    );
                })}
            </div>

            {/* Duplicate confirmation dialog */}
            {duplicateConfirm && (
                <>
                    <div className="taskbar-dialog-overlay" onClick={() => setDuplicateConfirm(null)} />
                    <div className="taskbar-dialog">
                        <div className="dialog-header">
                            <AlertCircle size={20} className="dialog-icon" />
                            <span>Source already exists</span>
                        </div>
                        <p className="dialog-message">
                            "<strong>{duplicateConfirm.existingName}</strong>" was already parsed from this URL.
                        </p>
                        <div className="dialog-actions">
                            <button
                                className="dialog-btn cancel"
                                onClick={() => handleDuplicateChoice('cancel')}
                            >
                                Cancel
                            </button>
                            <button
                                className="dialog-btn overwrite"
                                onClick={() => handleDuplicateChoice('overwrite')}
                            >
                                Overwrite
                            </button>
                            <button
                                className="dialog-btn keep-both"
                                onClick={() => handleDuplicateChoice('keep_both')}
                            >
                                Keep Both
                            </button>
                        </div>
                    </div>
                </>
            )}

            {/* Click outside to close menu */}
            {showMenu && (
                <div className="taskbar-menu-overlay" onClick={() => setShowMenu(false)} />
            )}
        </div>
    );
}
