// Writer App - BlockNote-based block editor
import "@blocknote/core/fonts/inter.css";
import "@blocknote/mantine/style.css";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";
import { SuggestionMenuController, getDefaultReactSlashMenuItems } from "@blocknote/react";
import { en } from "@blocknote/core/locales";
import './Writer.css';

interface WriterProps {
    artifactId?: string;
}

export function Writer({ artifactId }: WriterProps) {
    // Create editor instance with custom placeholder
    const editor = useCreateBlockNote({
        // Initial content - will load from artifact in Phase 4
        initialContent: artifactId ? undefined : undefined,
        // Override placeholder to use ? instead of /
        dictionary: {
            ...en,
            placeholders: {
                ...en.placeholders,
                default: "Enter text or type '?' for commands",
            },
        },
    });

    // Custom slash menu items (can extend later)
    const getMenuItems = (query: string) => {
        return getDefaultReactSlashMenuItems(editor).filter((item) =>
            item.title.toLowerCase().includes(query.toLowerCase())
        );
    };

    return (
        <div className="writer">
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
