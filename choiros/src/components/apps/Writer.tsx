// Writer App - BlockNote-based block editor
import "@blocknote/core/fonts/inter.css";
import "@blocknote/mantine/style.css";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";
import { SuggestionMenuController, getDefaultReactSlashMenuItems } from "@blocknote/react";
import { en } from "@blocknote/core/locales";
import { useEffect, useState } from 'react';
import { getArtifact } from '../../lib/api';
import './Writer.css';

interface WriterProps {
    artifactId?: string;
}

export function Writer({ artifactId }: WriterProps) {
    const [initialContent, setInitialContent] = useState<string | undefined>(undefined);
    const [isLoading, setIsLoading] = useState(!!artifactId);
    const [title, setTitle] = useState<string>('');

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
            <BlockNoteView
                editor={editor}
                slashMenu={false}  // Disable default "/" trigger
                theme="dark"
                onChange={() => {
                    // Debounced auto-save will come in Phase 4
                    console.log('[Writer] Content updated');
                }}
            >
                {/* Custom "?" triggered menu */}
                <SuggestionMenuController
                    triggerCharacter="?"
                    getItems={async (query) => getMenuItems(query)}
                />
            </BlockNoteView>
        </div>
    );
}
