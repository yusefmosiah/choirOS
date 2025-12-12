# ChoirOS Technology Stack

> Detailed technology choices with rationale for vibecoding.

---

## Frontend Stack

### Core Framework

| Choice | Package | Rationale |
|--------|---------|-----------|
| **Build** | Vite | Fast HMR, no SSR bloat, simple config |
| **View** | React 18 | Training data density, ecosystem, TipTap compatibility |
| **Language** | TypeScript | Type safety, better AI autocomplete |
| **State** | Zustand | Minimal boilerplate, fine-grained updates, no context hell |

```bash
npm create vite@latest choiros -- --template react-ts
npm install zustand
```

### UI Components

| Need | Package | Notes |
|------|---------|-------|
| **Rich Text Editor** | @tiptap/react | Notion-like, extensible, markdown export |
| **Window Dragging** | @dnd-kit/core | Modern, accessible, flexible |
| **Terminal** | @xterm/xterm | De facto standard, mature |
| **Icons** | lucide-react | Clean, tree-shakeable |

```bash
npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-placeholder
npm install @dnd-kit/core @dnd-kit/utilities
npm install @xterm/xterm @xterm/addon-fit
npm install lucide-react
```

### Data Layer (Browser)

| Need | Package | Notes |
|------|---------|-------|
| **SQLite** | sql.js | SQLite compiled to WASM |
| **NATS Client** | nats.ws | Official NATS WebSocket client |

```bash
npm install sql.js
npm install nats.ws
```

### CSS Strategy

**Vanilla CSS with CSS Custom Properties** (not Tailwind)

Rationale:
- Full control over desktop-like aesthetics
- No build complexity
- CSS custom properties for theming
- BEM naming for component styles

```css
/* Example: Window theming */
:root {
  --window-bg: #1a1a1a;
  --window-border: #333;
  --window-title-bg: #252525;
  --accent-gold: #d4af37;
}

.window {
  background: var(--window-bg);
  border: 1px solid var(--window-border);
}
```

---

## Backend Stack

### Event Bus

| Choice | Details |
|--------|---------|
| **NATS JetStream** | Latest stable (2.10+) |
| **Deployment** | EC2 cluster (3 nodes for HA) |
| **Client Auth** | JWT + NKey |

See [NATS.md](./NATS.md) for event schemas.

### Agent Isolation

| Choice | Details |
|--------|---------|
| **Firecracker** | v1.5+ |
| **Host** | EC2 .metal instances (e.g., c6i.metal) |
| **Orchestrator** | Custom Rust/Go service or Flintlock |

See [FIRECRACKER.md](./FIRECRACKER.md) for setup.

### Storage

| Need | Service | Details |
|------|---------|---------|
| **User State** | S3 | `s3://choiros-data/{user_id}/workspace.sqlite` |
| **Artifacts** | S3 | `s3://choiros-data/{user_id}/artifacts/*` |
| **Vectors** | Qdrant | Self-hosted on EC2, sharded by user |

### API Layer

| Choice | Details |
|--------|---------|
| **Runtime** | Python 3.12 + FastAPI |
| **Auth** | Passkey (WebAuthn) - integrate from tuxedo |
| **WebSocket** | NATS WebSocket gateway (nginx or custom) |

---

## Project Structure

```
choiros/
├── src/
│   ├── main.tsx                 # Entry point
│   ├── App.tsx                  # Root component
│   ├── stores/                  # Zustand stores
│   │   ├── windows.ts           # Window manager state
│   │   ├── filesystem.ts        # Virtual FS state
│   │   ├── nats.ts              # NATS connection state
│   │   └── user.ts              # Auth/session state
│   ├── components/
│   │   ├── desktop/
│   │   │   ├── Desktop.tsx      # Main desktop surface
│   │   │   ├── Taskbar.tsx      # Bottom bar with ? input
│   │   │   ├── Icon.tsx         # Desktop icons
│   │   │   └── Desktop.css
│   │   ├── window/
│   │   │   ├── Window.tsx       # Window chrome
│   │   │   ├── WindowManager.tsx
│   │   │   └── Window.css
│   │   └── apps/
│   │       ├── Writer.tsx       # TipTap editor app
│   │       ├── Files.tsx        # File explorer app
│   │       ├── Terminal.tsx     # xterm.js app
│   │       └── CommandBar.tsx   # The ? interface
│   ├── lib/
│   │   ├── db.ts                # sql.js wrapper
│   │   ├── nats.ts              # NATS client wrapper
│   │   ├── sync.ts              # S3 sync logic
│   │   └── events.ts            # Event type definitions
│   └── styles/
│       ├── reset.css            # CSS reset
│       ├── theme.css            # CSS custom properties
│       └── global.css           # Global styles
├── public/
│   └── sql-wasm.wasm            # sql.js WASM binary
├── docs/                        # This documentation
├── vite.config.ts
├── tsconfig.json
└── package.json
```

---

## Development Commands

```bash
# Install
npm install

# Dev server
npm run dev

# Type check
npm run typecheck

# Build
npm run build

# Preview production build
npm run preview
```

---

## Key Dependencies Summary

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "zustand": "^4.5.0",
    "@tiptap/react": "^2.4.0",
    "@tiptap/starter-kit": "^2.4.0",
    "@dnd-kit/core": "^6.1.0",
    "@xterm/xterm": "^5.5.0",
    "sql.js": "^1.10.0",
    "nats.ws": "^1.28.0",
    "lucide-react": "^0.400.0"
  },
  "devDependencies": {
    "vite": "^5.4.0",
    "typescript": "^5.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0"
  }
}
```
