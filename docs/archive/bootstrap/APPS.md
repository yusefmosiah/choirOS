# ChoirOS Applications

> Specifications for Writer, Files, Terminal, and the ? bar.
> NATS references in this doc are deferred; v0 uses local state and git only.

---

## App Registry

```typescript
// lib/apps.ts
export const APP_REGISTRY = {
  writer: {
    id: 'writer',
    title: 'Writer',
    icon: 'file-text',
    component: () => import('./components/apps/Writer'),
    defaultSize: { width: 800, height: 600 },
    fileTypes: ['.md', '.txt', '.json'],
  },
  files: {
    id: 'files',
    title: 'Files',
    icon: 'folder',
    component: () => import('./components/apps/Files'),
    defaultSize: { width: 700, height: 500 },
  },
  terminal: {
    id: 'terminal',
    title: 'Terminal',
    icon: 'terminal',
    component: () => import('./components/apps/Terminal'),
    defaultSize: { width: 700, height: 450 },
  },
} as const;
```

---

## Writer (TipTap)

The primary document editing app. Notion-like rich text with markdown export.

### Features

- Rich text formatting (bold, italic, headings, lists)
- Slash commands (`/heading`, `/list`, `/quote`)
- Markdown import/export
- Auto-save to SQLite
- Local events for agent observation (NATS later)

### Component

```tsx
// components/apps/Writer.tsx
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';

interface WriterProps {
  artifactId?: string;  // If opening existing file
}

export function Writer({ artifactId }: WriterProps) {
  const [content, setContent] = useState('');
  const saveArtifact = useArtifactStore(s => s.save);
  const publishEvent = useEventStore(s => s.publish);

  // Load existing artifact if provided
  useEffect(() => {
    if (artifactId) {
      loadArtifact(artifactId).then(setContent);
    }
  }, [artifactId]);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: 'Start writing...',
      }),
    ],
    content,
    onUpdate: ({ editor }) => {
      // Debounced auto-save
      debouncedSave(artifactId, editor.getHTML());
    },
  });

  // Emit local event on significant changes (NATS later)
  const handleBlur = () => {
    if (editor && artifactId) {
      publishEvent(`choiros.user.${userId}.file.UPDATED`, {
        artifact_id: artifactId,
        content_preview: editor.getText().slice(0, 200),
      });
    }
  };

  return (
    <div className="writer">
      <WriterToolbar editor={editor} />
      <EditorContent
        editor={editor}
        className="writer-content"
        onBlur={handleBlur}
      />
    </div>
  );
}
```

### Toolbar

```tsx
// components/apps/WriterToolbar.tsx
export function WriterToolbar({ editor }: { editor: Editor | null }) {
  if (!editor) return null;

  return (
    <div className="writer-toolbar">
      <button
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={editor.isActive('bold') ? 'active' : ''}
      >
        <Bold size={16} />
      </button>
      <button
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={editor.isActive('italic') ? 'active' : ''}
      >
        <Italic size={16} />
      </button>
      <div className="toolbar-divider" />
      <button
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        className={editor.isActive('heading', { level: 1 }) ? 'active' : ''}
      >
        H1
      </button>
      <button
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        className={editor.isActive('heading', { level: 2 }) ? 'active' : ''}
      >
        H2
      </button>
      <div className="toolbar-divider" />
      <button
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={editor.isActive('bulletList') ? 'active' : ''}
      >
        <List size={16} />
      </button>
    </div>
  );
}
```

### CSS

```css
/* styles/apps/writer.css */
.writer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

.writer-toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.writer-toolbar button {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}

.writer-toolbar button:hover,
.writer-toolbar button.active {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.writer-content {
  flex: 1;
  padding: var(--spacing-lg);
  overflow-y: auto;
}

.writer-content .ProseMirror {
  min-height: 100%;
  outline: none;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-primary);
}

.writer-content .ProseMirror p.is-editor-empty:first-child::before {
  color: var(--text-secondary);
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}
```

---

## Files

File explorer for browsing artifacts stored in SQLite/S3.

### Features

- Grid and list view
- Folder navigation
- File preview on select
- Double-click to open in appropriate app
- Create new folder/file
- Delete, rename

### Component

```tsx
// components/apps/Files.tsx
export function Files() {
  const [currentPath, setCurrentPath] = useState('/');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selected, setSelected] = useState<string | null>(null);

  const artifacts = useArtifactStore(s => s.listDirectory(currentPath));
  const openWindow = useWindowStore(s => s.openWindow);

  const handleDoubleClick = (artifact: Artifact) => {
    if (artifact.type === 'folder') {
      setCurrentPath(artifact.path);
    } else {
      // Open in appropriate app
      const appId = getAppForFileType(artifact.mimeType);
      openWindow(appId, { artifactId: artifact.id });
    }
  };

  return (
    <div className="files">
      <FilesToolbar
        path={currentPath}
        onNavigate={setCurrentPath}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      <div className={`files-grid files-${viewMode}`}>
        {artifacts.map(artifact => (
          <FileItem
            key={artifact.id}
            artifact={artifact}
            isSelected={selected === artifact.id}
            onClick={() => setSelected(artifact.id)}
            onDoubleClick={() => handleDoubleClick(artifact)}
          />
        ))}
      </div>
    </div>
  );
}
```

### File Item

```tsx
// components/apps/FileItem.tsx
export function FileItem({ artifact, isSelected, onClick, onDoubleClick }: Props) {
  const Icon = getIconForType(artifact.mimeType);

  return (
    <div
      className={`file-item ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
    >
      <div className="file-icon">
        <Icon size={48} />
      </div>
      <span className="file-name">{artifact.name}</span>
    </div>
  );
}
```

### CSS

```css
/* styles/apps/files.css */
.files {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

.files-toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.files-grid {
  flex: 1;
  padding: var(--spacing-md);
  overflow-y: auto;
}

.files-grid.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: var(--spacing-md);
}

.files-grid.files-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.file-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.15s;
}

.file-item:hover {
  background: var(--bg-secondary);
}

.file-item.selected {
  background: var(--bg-tertiary);
  outline: 1px solid var(--accent-gold-dim);
}

.file-icon {
  color: var(--text-secondary);
}

.file-name {
  margin-top: var(--spacing-xs);
  font-size: 12px;
  color: var(--text-primary);
  text-align: center;
  word-break: break-word;
}
```

---

## Terminal

xterm.js-based terminal for power users and agent output.

### Features

- Full terminal emulation
- Connect to agent VM output streams
- Local command history
- Copy/paste support

### Component

```tsx
// components/apps/Terminal.tsx
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

export function Terminal() {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    const xterm = new XTerm({
      theme: {
        background: '#0d0d0d',
        foreground: '#e0e0e0',
        cursor: '#d4af37',
        cursorAccent: '#0d0d0d',
      },
      fontFamily: 'JetBrains Mono, Menlo, Monaco, monospace',
      fontSize: 14,
      cursorBlink: true,
    });

    const fitAddon = new FitAddon();
    xterm.loadAddon(fitAddon);

    xterm.open(terminalRef.current);
    fitAddon.fit();

    // Handle window resize
    const resizeObserver = new ResizeObserver(() => fitAddon.fit());
    resizeObserver.observe(terminalRef.current);

    // Welcome message
    xterm.writeln('ChoirOS Terminal v0.1.0');
    xterm.writeln('Type "help" for available commands.\n');
    xterm.write('$ ');

    // Handle input
    let currentLine = '';
    xterm.onKey(({ key, domEvent }) => {
      if (domEvent.key === 'Enter') {
        xterm.writeln('');
        handleCommand(currentLine, xterm);
        currentLine = '';
        xterm.write('$ ');
      } else if (domEvent.key === 'Backspace') {
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1);
          xterm.write('\b \b');
        }
      } else if (key.length === 1) {
        currentLine += key;
        xterm.write(key);
      }
    });

    xtermRef.current = xterm;

    return () => {
      resizeObserver.disconnect();
      xterm.dispose();
    };
  }, []);

  return <div ref={terminalRef} className="terminal" />;
}

function handleCommand(cmd: string, xterm: XTerm) {
  const trimmed = cmd.trim();

  if (trimmed === 'help') {
    xterm.writeln('Available commands:');
    xterm.writeln('  help     - Show this message');
    xterm.writeln('  clear    - Clear terminal');
    xterm.writeln('  status   - Show system status');
    xterm.writeln('  agents   - List running agents');
  } else if (trimmed === 'clear') {
    xterm.clear();
  } else if (trimmed === 'status') {
    xterm.writeln('Connected: ✓');
    xterm.writeln('SQLite synced: ✓');
  } else if (trimmed) {
    xterm.writeln(`Unknown command: ${trimmed}`);
  }
}
```

### CSS

```css
/* styles/apps/terminal.css */
.terminal {
  width: 100%;
  height: 100%;
  background: #0d0d0d;
  padding: var(--spacing-sm);
}

.terminal .xterm-viewport {
  overflow-y: auto;
}
```

---

## Command Bar (? Interface)

The global command interface - not a separate app, but integrated in the taskbar.

### Command Types

| Prefix | Meaning | Example |
|--------|---------|---------|
| `?` | System command | `?new doc`, `?open`, `?help` |
| (none) | Natural language to agent | "Summarize this document" |

### Command Handler

```typescript
// lib/commands.ts
export interface CommandResult {
  type: 'action' | 'error' | 'output';
  message?: string;
}

export async function executeCommand(input: string): Promise<CommandResult> {
  const parts = input.trim().split(' ');
  const cmd = parts[0].toLowerCase();
  const args = parts.slice(1);

  switch (cmd) {
    case 'new':
      return handleNew(args);
    case 'open':
      return handleOpen(args);
    case 'search':
      return handleSearch(args);
    case 'help':
      return handleHelp();
    default:
      return { type: 'error', message: `Unknown command: ${cmd}` };
  }
}

function handleNew(args: string[]): CommandResult {
  const type = args[0] || 'doc';
  const openWindow = useWindowStore.getState().openWindow;

  if (type === 'doc' || type === 'document') {
    const id = createNewArtifact('document');
    openWindow('writer', { artifactId: id });
    return { type: 'action', message: 'Created new document' };
  }

  return { type: 'error', message: `Unknown type: ${type}` };
}

function handleHelp(): CommandResult {
  return {
    type: 'output',
    message: `
Commands:
  ?new doc     - Create new document
  ?open        - Open file picker
  ?search X    - Search for X
  ?settings    - Open settings
  ?help        - Show this message
    `.trim(),
  };
}
```

### Natural Language Handler

```typescript
// lib/agent.ts
export async function sendToAgent(input: string): Promise<void> {
  const userId = useUserStore.getState().userId;
  const focusedWindowId = useWindowStore.getState().focusedWindowId;

  // Get context from focused window
  const context = focusedWindowId
    ? getWindowContext(focusedWindowId)
    : null;

  // Emit local event for agent processing (NATS later)
  await publishEvent(`choiros.user.${userId}.action.COMMAND`, {
    natural_language: input,
    context: {
      focused_artifact_id: context?.artifactId,
      focused_app: context?.appId,
    },
    timestamp: Date.now(),
  });

  // Show pending indicator
  showNotification('Thinking...', { type: 'loading' });
}
```

---

## App Communication

Apps communicate through the Zustand stores and local events. NATS is deferred.

```typescript
// Example: Writer emits event, Files updates
// 1. Writer saves artifact
saveArtifact(id, content);
publishEvent(`choiros.user.${userId}.file.UPDATED`, { artifact_id: id });

// 2. Files subscribes to file events
subscribeToEvent(`choiros.user.${userId}.file.*`, (event) => {
  if (event.type === 'UPDATED') {
    refreshDirectory(currentPath);
  }
});
```
