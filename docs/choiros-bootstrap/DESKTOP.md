# Desktop Shell Specification

> Window manager, taskbar, and shell components.

---

## Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Desktop                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Wallpaper Layer                      ││
│  ├─────────────────────────────────────────────────────────┤│
│  │                    Icon Layer                           ││
│  │   📄 Files    📝 Writer    ⌨️ Terminal                   ││
│  ├─────────────────────────────────────────────────────────┤│
│  │                   Window Layer                          ││
│  │   ┌─────────────────────┐                               ││
│  │   │ Window (z-index: n) │                               ││
│  │   └─────────────────────┘                               ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│ [ ? ] [ __________________________________________ ] [≡] [🔔]│
│                        Taskbar                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Window Manager

### Window State

```typescript
interface WindowState {
  id: string;
  appId: string;                    // "writer" | "files" | "terminal"
  title: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  zIndex: number;
  isMinimized: boolean;
  isMaximized: boolean;
  isFocused: boolean;
}

interface WindowManagerState {
  windows: Map<string, WindowState>;
  focusedWindowId: string | null;
  nextZIndex: number;
}
```

### Zustand Store

```typescript
// stores/windows.ts
import { create } from 'zustand';

interface WindowStore extends WindowManagerState {
  openWindow: (appId: string, props?: Partial<WindowState>) => string;
  closeWindow: (id: string) => void;
  focusWindow: (id: string) => void;
  minimizeWindow: (id: string) => void;
  maximizeWindow: (id: string) => void;
  moveWindow: (id: string, x: number, y: number) => void;
  resizeWindow: (id: string, width: number, height: number) => void;
}

export const useWindowStore = create<WindowStore>((set, get) => ({
  windows: new Map(),
  focusedWindowId: null,
  nextZIndex: 1,

  openWindow: (appId, props = {}) => {
    const id = crypto.randomUUID();
    const { nextZIndex } = get();

    const window: WindowState = {
      id,
      appId,
      title: getAppTitle(appId),
      position: { x: 100 + (nextZIndex * 20), y: 100 + (nextZIndex * 20) },
      size: getDefaultSize(appId),
      zIndex: nextZIndex,
      isMinimized: false,
      isMaximized: false,
      isFocused: true,
      ...props,
    };

    set(state => ({
      windows: new Map(state.windows).set(id, window),
      focusedWindowId: id,
      nextZIndex: nextZIndex + 1,
    }));

    return id;
  },

  // ... other actions
}));
```

### Window Component

```tsx
// components/window/Window.tsx
interface WindowProps {
  id: string;
  children: React.ReactNode;
}

export function Window({ id, children }: WindowProps) {
  const window = useWindowStore(s => s.windows.get(id));
  const focusWindow = useWindowStore(s => s.focusWindow);
  const closeWindow = useWindowStore(s => s.closeWindow);

  if (!window || window.isMinimized) return null;

  return (
    <div
      className="window"
      style={{
        transform: `translate(${window.position.x}px, ${window.position.y}px)`,
        width: window.size.width,
        height: window.size.height,
        zIndex: window.zIndex,
      }}
      onMouseDown={() => focusWindow(id)}
    >
      <div className="window-titlebar">
        <span className="window-title">{window.title}</span>
        <div className="window-controls">
          <button onClick={() => minimizeWindow(id)}>−</button>
          <button onClick={() => maximizeWindow(id)}>□</button>
          <button onClick={() => closeWindow(id)}>×</button>
        </div>
      </div>
      <div className="window-content">
        {children}
      </div>
    </div>
  );
}
```

### Drag & Resize with dnd-kit

```typescript
// hooks/useWindowDrag.ts
import { useDraggable } from '@dnd-kit/core';

export function useWindowDrag(windowId: string) {
  const moveWindow = useWindowStore(s => s.moveWindow);

  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: `window-drag-${windowId}`,
  });

  // Apply transform during drag, commit on drop
  return { attributes, listeners, setNodeRef, transform };
}
```

---

## Taskbar

### Structure

```
┌────────────────────────────────────────────────────────────────┐
│ [?] │ [_____________________________________________] │ [≡][🔔]│
│ btn │              Command Input                      │  tray  │
└────────────────────────────────────────────────────────────────┘
```

### Component

```tsx
// components/desktop/Taskbar.tsx
export function Taskbar() {
  const [input, setInput] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.startsWith('?')) {
      executeCommand(input.slice(1).trim());
    } else {
      sendToAgent(input);
    }
    setInput('');
  };

  return (
    <div className="taskbar">
      <button
        className="taskbar-menu-btn"
        onClick={() => setMenuOpen(!menuOpen)}
      >
        ?
      </button>

      {menuOpen && <CommandMenu onSelect={setInput} onClose={() => setMenuOpen(false)} />}

      <form className="taskbar-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="taskbar-input"
          placeholder="Ask anything or type ? for commands..."
          value={input}
          onChange={e => setInput(e.target.value)}
        />
      </form>

      <div className="taskbar-tray">
        <RunningApps />
        <NotificationBell />
      </div>
    </div>
  );
}
```

### Command Menu

```tsx
// components/desktop/CommandMenu.tsx
const COMMANDS = [
  { label: 'New document', command: '?new doc' },
  { label: 'Open file...', command: '?open' },
  { label: 'Search files', command: '?search' },
  { label: 'Settings', command: '?settings' },
  { label: 'Help', command: '?help' },
];

export function CommandMenu({ onSelect, onClose }: Props) {
  return (
    <div className="command-menu">
      {COMMANDS.map(cmd => (
        <button
          key={cmd.command}
          onClick={() => {
            onSelect(cmd.command);
            onClose();
          }}
        >
          {cmd.label}
        </button>
      ))}
    </div>
  );
}
```

---

## Desktop Icons

### Icon Grid

```tsx
// components/desktop/Desktop.tsx
const DESKTOP_ICONS = [
  { id: 'files', label: 'Files', icon: FolderIcon },
  { id: 'writer', label: 'Writer', icon: FileTextIcon },
  { id: 'terminal', label: 'Terminal', icon: TerminalIcon },
];

export function Desktop() {
  const openWindow = useWindowStore(s => s.openWindow);

  return (
    <div className="desktop">
      <div className="desktop-wallpaper" />

      <div className="desktop-icons">
        {DESKTOP_ICONS.map(icon => (
          <DesktopIcon
            key={icon.id}
            label={icon.label}
            icon={icon.icon}
            onDoubleClick={() => openWindow(icon.id)}
          />
        ))}
      </div>

      <WindowManager />
      <Taskbar />
    </div>
  );
}
```

---

## CSS Architecture

### Theme Variables

```css
/* styles/theme.css */
:root {
  /* Colors - Carbon Fiber Kintsugi */
  --bg-primary: #0d0d0d;
  --bg-secondary: #1a1a1a;
  --bg-tertiary: #252525;
  --border-color: #333;
  --text-primary: #e0e0e0;
  --text-secondary: #888;
  --accent-gold: #d4af37;
  --accent-gold-dim: #8b7355;

  /* Window */
  --window-bg: var(--bg-secondary);
  --window-border: var(--border-color);
  --window-titlebar-bg: var(--bg-tertiary);
  --window-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);

  /* Taskbar */
  --taskbar-height: 48px;
  --taskbar-bg: rgba(13, 13, 13, 0.9);
  --taskbar-blur: 12px;

  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;

  /* Borders */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}
```

### Window Styles

```css
/* styles/components/window.css */
.window {
  position: absolute;
  background: var(--window-bg);
  border: 1px solid var(--window-border);
  border-radius: var(--radius-md);
  box-shadow: var(--window-shadow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.window.focused {
  border-color: var(--accent-gold-dim);
}

.window-titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 36px;
  padding: 0 var(--spacing-sm);
  background: var(--window-titlebar-bg);
  cursor: grab;
  user-select: none;
}

.window-titlebar:active {
  cursor: grabbing;
}

.window-title {
  font-size: 13px;
  color: var(--text-primary);
}

.window-controls {
  display: flex;
  gap: var(--spacing-xs);
}

.window-controls button {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.15s;
}

.window-controls button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.window-controls button:last-child:hover {
  background: #e81123;
  color: white;
}

.window-content {
  flex: 1;
  overflow: auto;
}
```

### Taskbar Styles

```css
/* styles/components/taskbar.css */
.taskbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--taskbar-height);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 0 var(--spacing-md);
  background: var(--taskbar-bg);
  backdrop-filter: blur(var(--taskbar-blur));
  border-top: 1px solid var(--border-color);
}

.taskbar-menu-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--accent-gold-dim);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--accent-gold);
  font-size: 20px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.15s;
}

.taskbar-menu-btn:hover {
  background: var(--accent-gold);
  color: var(--bg-primary);
}

.taskbar-input-form {
  flex: 1;
}

.taskbar-input {
  width: 100%;
  height: 36px;
  padding: 0 var(--spacing-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 14px;
}

.taskbar-input:focus {
  outline: none;
  border-color: var(--accent-gold-dim);
}

.taskbar-input::placeholder {
  color: var(--text-secondary);
}
```

---

## Responsive Behavior

```css
/* Mobile: Stack taskbar, hide desktop icons */
@media (max-width: 768px) {
  .desktop-icons {
    display: none;
  }

  .window {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: calc(100% - var(--taskbar-height)) !important;
    border-radius: 0;
  }
}
```
