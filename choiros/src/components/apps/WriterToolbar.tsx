// Writer Toolbar
import type { Editor } from '@tiptap/react';
import { Bold, Italic, Strikethrough, List, ListOrdered, Quote, Code, Heading1, Heading2, Undo, Redo } from 'lucide-react';
import './WriterToolbar.css';

interface WriterToolbarProps {
    editor: Editor | null;
}

interface ToolbarButton {
    icon: React.ReactNode;
    title: string;
    action: () => void;
    isActive?: () => boolean;
}

export function WriterToolbar({ editor }: WriterToolbarProps) {
    if (!editor) return null;

    const buttons: ToolbarButton[] = [
        {
            icon: <Bold size={16} />,
            title: 'Bold',
            action: () => editor.chain().focus().toggleBold().run(),
            isActive: () => editor.isActive('bold'),
        },
        {
            icon: <Italic size={16} />,
            title: 'Italic',
            action: () => editor.chain().focus().toggleItalic().run(),
            isActive: () => editor.isActive('italic'),
        },
        {
            icon: <Strikethrough size={16} />,
            title: 'Strikethrough',
            action: () => editor.chain().focus().toggleStrike().run(),
            isActive: () => editor.isActive('strike'),
        },
        {
            icon: <Code size={16} />,
            title: 'Code',
            action: () => editor.chain().focus().toggleCode().run(),
            isActive: () => editor.isActive('code'),
        },
    ];

    const headingButtons: ToolbarButton[] = [
        {
            icon: <Heading1 size={16} />,
            title: 'Heading 1',
            action: () => editor.chain().focus().toggleHeading({ level: 1 }).run(),
            isActive: () => editor.isActive('heading', { level: 1 }),
        },
        {
            icon: <Heading2 size={16} />,
            title: 'Heading 2',
            action: () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
            isActive: () => editor.isActive('heading', { level: 2 }),
        },
    ];

    const listButtons: ToolbarButton[] = [
        {
            icon: <List size={16} />,
            title: 'Bullet List',
            action: () => editor.chain().focus().toggleBulletList().run(),
            isActive: () => editor.isActive('bulletList'),
        },
        {
            icon: <ListOrdered size={16} />,
            title: 'Ordered List',
            action: () => editor.chain().focus().toggleOrderedList().run(),
            isActive: () => editor.isActive('orderedList'),
        },
        {
            icon: <Quote size={16} />,
            title: 'Blockquote',
            action: () => editor.chain().focus().toggleBlockquote().run(),
            isActive: () => editor.isActive('blockquote'),
        },
    ];

    const historyButtons: ToolbarButton[] = [
        {
            icon: <Undo size={16} />,
            title: 'Undo',
            action: () => editor.chain().focus().undo().run(),
        },
        {
            icon: <Redo size={16} />,
            title: 'Redo',
            action: () => editor.chain().focus().redo().run(),
        },
    ];

    return (
        <div className="writer-toolbar">
            <div className="toolbar-group">
                {buttons.map((btn, i) => (
                    <button
                        key={i}
                        className={`toolbar-button ${btn.isActive?.() ? 'active' : ''}`}
                        onClick={btn.action}
                        title={btn.title}
                        type="button"
                    >
                        {btn.icon}
                    </button>
                ))}
            </div>

            <div className="toolbar-divider" />

            <div className="toolbar-group">
                {headingButtons.map((btn, i) => (
                    <button
                        key={i}
                        className={`toolbar-button ${btn.isActive?.() ? 'active' : ''}`}
                        onClick={btn.action}
                        title={btn.title}
                        type="button"
                    >
                        {btn.icon}
                    </button>
                ))}
            </div>

            <div className="toolbar-divider" />

            <div className="toolbar-group">
                {listButtons.map((btn, i) => (
                    <button
                        key={i}
                        className={`toolbar-button ${btn.isActive?.() ? 'active' : ''}`}
                        onClick={btn.action}
                        title={btn.title}
                        type="button"
                    >
                        {btn.icon}
                    </button>
                ))}
            </div>

            <div className="toolbar-spacer" />

            <div className="toolbar-group">
                {historyButtons.map((btn, i) => (
                    <button
                        key={i}
                        className="toolbar-button"
                        onClick={btn.action}
                        title={btn.title}
                        type="button"
                    >
                        {btn.icon}
                    </button>
                ))}
            </div>
        </div>
    );
}
