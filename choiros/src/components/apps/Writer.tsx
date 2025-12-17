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

    // Custom slash menu items (can extend later)
    const getMenuItems = (query: string) => {
        return getDefaultReactSlashMenuItems(editor).filter((item) =>
            item.title.toLowerCase().includes(query.toLowerCase())
        );
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
