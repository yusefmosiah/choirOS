// Writer App - BlockNote-based block editor
import "@blocknote/core/fonts/inter.css";
import "@blocknote/mantine/style.css";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";
import { SuggestionMenuController, getDefaultReactSlashMenuItems } from "@blocknote/react";
import { en } from "@blocknote/core/locales";
import { useCallback, useEffect, useRef, useState } from 'react';
import { getArtifact } from '../../lib/api';
import { authFetch } from '../../lib/auth';
import { useAgent, type AgentMessage } from '../../hooks/useAgent';
import { useWindowStore } from '../../stores/windows';
import './Writer.css';

interface WriterProps {
    artifactId?: string;
    filePath?: string;
    initialPrompt?: string;
}

export function Writer({ artifactId, filePath, initialPrompt }: WriterProps) {
    const [initialContent, setInitialContent] = useState<string | undefined>(undefined);
    const [isLoading, setIsLoading] = useState(!!artifactId);
    const [title, setTitle] = useState<string>('');
    const [conversation, setConversation] = useState<Array<{ id: string; role: 'user' | 'assistant' | 'system'; content: string }>>([]);
    const [draftPrompt, setDraftPrompt] = useState('');
    const hasSentInitialPrompt = useRef(false);
    const openWindow = useWindowStore((s) => s.openWindow);
    const windows = useWindowStore((s) => s.windows);
    const focusWindow = useWindowStore((s) => s.focusWindow);
    const restoreWindow = useWindowStore((s) => s.restoreWindow);
    const { sendPrompt, isProcessing, isConnected } = useAgent({
        onMessage: (message: AgentMessage) => {
            if (message.type === 'text' && typeof message.content === 'string') {
                setConversation((prev) => [
                    ...prev,
                    { id: crypto.randomUUID(), role: 'assistant', content: message.content },
                ]);
            } else if (message.type === 'tool_use' && typeof message.content === 'object') {
                const tool = (message.content as { tool?: string })?.tool || 'tool';
                setConversation((prev) => [
                    ...prev,
                    { id: crypto.randomUUID(), role: 'system', content: `Using ${tool}...` },
                ]);
            } else if (message.type === 'error') {
                setConversation((prev) => [
                    ...prev,
                    { id: crypto.randomUUID(), role: 'system', content: String(message.content) },
                ]);
            }
        },
    });

    const ensureContextHeatmap = useCallback(() => {
        const existing = Array.from(windows.values()).find((win) => win.appId === 'contextHeatmap');
        if (existing) {
            if (existing.isMinimized) {
                restoreWindow(existing.id);
            }
            focusWindow(existing.id);
            return;
        }
        openWindow('contextHeatmap');
    }, [windows, openWindow, focusWindow, restoreWindow]);

    const handleSendPrompt = useCallback((prompt: string) => {
        const trimmed = prompt.trim();
        if (!trimmed) return;
        if (!isConnected) {
            setConversation((prev) => [
                ...prev,
                { id: crypto.randomUUID(), role: 'system', content: 'Agent not connected.' },
            ]);
            return;
        }
        ensureContextHeatmap();
        setConversation((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: 'user', content: trimmed },
        ]);
        sendPrompt(trimmed);
        setDraftPrompt('');
    }, [isConnected, sendPrompt, ensureContextHeatmap]);

    // Load artifact content if artifactId is provided
    useEffect(() => {
        if (artifactId) {
            setIsLoading(true);
            getArtifact(artifactId)
                .then((artifact) => {
                    setInitialContent(artifact.content);
                    setTitle(artifact.name);
                    setIsLoading(false);
                })
                .catch((err) => {
                    console.error('[Writer] Failed to load artifact:', err);
                    setIsLoading(false);
                });
        }
    }, [artifactId]);

    useEffect(() => {
        if (!filePath) {
            return;
        }
        setIsLoading(true);
        const url = `${import.meta.env.VITE_SUPERVISOR_URL || 'http://localhost:8001'}/observability/file?path=${encodeURIComponent(filePath)}`;
        authFetch(url)
            .then(async (response) => {
                if (!response.ok) {
                    throw new Error('Failed to load file');
                }
                const data = await response.json() as { content: string; path: string };
                setInitialContent(data.content);
                setTitle(data.path);
            })
            .catch((err) => {
                console.error('[Writer] Failed to load file:', err);
            })
            .finally(() => setIsLoading(false));
    }, [filePath]);

    // Create editor instance with custom placeholder
    const editor = useCreateBlockNote({
        // Override placeholder to use ? instead of /
        dictionary: {
            ...en,
            placeholders: {
                ...en.placeholders,
                default: "Enter text or type '?' for commands",
            },
        },
    });

    // Update editor content when artifact loads
    useEffect(() => {
        if (initialContent && editor) {
            // Split content into lines and create paragraph blocks
            try {
                const lines = initialContent.split('\n').filter(line => line.trim());
                const blocks = lines.map(line => ({
                    type: "paragraph" as const,
                    content: line,
                }));
                if (blocks.length > 0) {
                    editor.replaceBlocks(editor.document, blocks);
                }
            } catch (e) {
                console.error('[Writer] Failed to set content:', e);
            }
        }
    }, [initialContent, editor]);

    useEffect(() => {
        if (!hasSentInitialPrompt.current && initialPrompt) {
            hasSentInitialPrompt.current = true;
            handleSendPrompt(initialPrompt);
        }
    }, [initialPrompt, handleSendPrompt]);

    // Custom slash menu items
    const getMenuItems = (query: string) => {
        const defaultItems = getDefaultReactSlashMenuItems(editor);

        // Add "Audit Link" item
        const auditItem = {
            title: "Audit Link",
            onItemClick: () => {
                const url = window.prompt("Enter URL to audit:");
                if (url) {
                    scanUrl(url);
                }
            },
            aliases: ["audit", "check", "verify"],
            group: "Tools",
            icon: (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
            ),
            subtext: "Run Unilateral Auditor on a URL",
        };

        return [auditItem, ...defaultItems].filter((item) =>
            item.title.toLowerCase().includes(query.toLowerCase())
        );
    };

    // Handle Audit Streaming
    const scanUrl = async (url: string) => {
        if (!editor) return;

        // Insert placeholder block
        editor.insertBlocks(
            [
                {
                    type: "paragraph",
                    content: `🔍 Auditing ${url}...`,
                },
            ],
            editor.document[editor.document.length - 1],
            "after"
        );

        try {
            const response = await fetch("http://localhost:8001/agent/audit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ task: "Audit this link", url }),
            });

            if (!response.body) return;

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split("\n\n");

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === "critique") {
                            // Append critique to editor
                            editor.insertBlocks(
                                [
                                    {
                                        type: "paragraph",
                                        content: "📝 CRITIQUE:",
                                    },
                                    {
                                        type: "paragraph",
                                        content: data.content,
                                    }
                                ],
                                editor.document[editor.document.length - 1],
                                "after"
                            );
                        } else if (data.type === "mode") {
                            editor.insertBlocks(
                                [
                                    {
                                        type: "paragraph",
                                        content: `Tone: ${data.content}`,
                                    }
                                ],
                                editor.document[editor.document.length - 1],
                                "after"
                            );
                        } else if (data.type === "blind_spots") {
                            const items = Array.isArray(data.content) ? data.content : [String(data.content)];
                            editor.insertBlocks(
                                [
                                    { type: "paragraph", content: "⚠️ BLIND SPOTS:" },
                                    ...items.map((item: string) => ({
                                        type: "paragraph",
                                        content: `- ${item}`,
                                    })),
                                ],
                                editor.document[editor.document.length - 1],
                                "after"
                            );
                        } else if (data.type === "citations") {
                            const items = Array.isArray(data.content) ? data.content : [String(data.content)];
                            editor.insertBlocks(
                                [
                                    { type: "paragraph", content: "🔗 SOURCES / QUERIES:" },
                                    ...items.map((item: string) => ({
                                        type: "paragraph",
                                        content: `- ${item}`,
                                    })),
                                ],
                                editor.document[editor.document.length - 1],
                                "after"
                            );
                        }
                    }
                }
            }
        } catch (e) {
            console.error("Audit failed", e);
            editor.insertBlocks(
                [
                    {
                        type: "paragraph",
                        content: `❌ Audit failed: ${e}`,
                    }
                ],
                editor.document[editor.document.length - 1],
                "after"
            );
        }
    };

    if (isLoading) {
        return (
            <div className="writer writer-loading">
                <div className="loading-spinner">Loading...</div>
            </div>
        );
    }

    return (
        <div className="writer">
            {title && (
                <div className="writer-title-bar">
                    <span className="writer-title">{title}</span>
                </div>
            )}
            <div className="writer-body">
                <div className="writer-chat">
                    <div className="writer-chat-header">
                        <span>Conversation</span>
                        <span className={`writer-chat-status ${isConnected ? 'connected' : 'disconnected'}`}>
                            {isConnected ? 'Agent online' : 'Agent offline'}
                        </span>
                    </div>
                    <div className="writer-chat-messages">
                        {conversation.length === 0 ? (
                            <div className="writer-chat-empty">Start a conversation to capture agent context.</div>
                        ) : (
                            conversation.map((message) => (
                                <div key={message.id} className={`writer-chat-message ${message.role}`}>
                                    <div className="writer-chat-role">{message.role}</div>
                                    <div className="writer-chat-content">{message.content}</div>
                                </div>
                            ))
                        )}
                    </div>
                    <form
                        className="writer-chat-input"
                        onSubmit={(event) => {
                            event.preventDefault();
                            handleSendPrompt(draftPrompt);
                        }}
                    >
                        <input
                            type="text"
                            value={draftPrompt}
                            onChange={(event) => setDraftPrompt(event.target.value)}
                            placeholder={isProcessing ? 'Agent thinking...' : 'Ask the agent...'}
                            disabled={isProcessing}
                        />
                        <button type="submit" disabled={isProcessing || !draftPrompt.trim()}>
                            Send
                        </button>
                    </form>
                </div>
                <div className="writer-editor">
                    <BlockNoteView
                        editor={editor}
                        slashMenu={false}
                        theme="dark"
                        onChange={() => {
                            console.log('[Writer] Content updated');
                        }}
                    >
                        <SuggestionMenuController
                            triggerCharacter="?"
                            getItems={async (query) => getMenuItems(query)}
                        />
                    </BlockNoteView>
                </div>
            </div>
        </div>
    );
}
