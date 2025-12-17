// Writer App - TipTap-based rich text editor
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { WriterToolbar } from './WriterToolbar';
import './Writer.css';

interface WriterProps {
    artifactId?: string;
}

export function Writer({ artifactId }: WriterProps) {
    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                heading: {
                    levels: [1, 2, 3],
                },
            }),
            Placeholder.configure({
                placeholder: 'Start writing...',
            }),
        ],
        content: artifactId ? '' : '', // Will load from artifact in Phase 4
        editorProps: {
            attributes: {
                class: 'writer-editor',
            },
        },
        onUpdate: ({ editor }) => {
            // Debounced auto-save will come in Phase 4 (persistence)
            console.log('[Writer] Content updated:', editor.getText().slice(0, 50) + '...');
        },
    });

    return (
        <div className="writer">
            <WriterToolbar editor={editor} />
            <div className="writer-content">
                <EditorContent editor={editor} />
            </div>
        </div>
    );
}
