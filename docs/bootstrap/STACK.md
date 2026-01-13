# ChoirOS Technology Stack (v0)

> Focused on Ralph-in-Ralph, Sprites-first, Vite-in-Associate.

---

## Frontend Stack

### Core Framework

| Choice | Package | Rationale |
|--------|---------|-----------|
| **Build** | Vite | Fast HMR, no SSR bloat, simple config |
| **View** | React 18 | Training data density, ecosystem |
| **Language** | TypeScript | Type safety, better AI autocomplete |
| **State** | Zustand | Minimal boilerplate, fine-grained updates |

```bash
npm create vite@latest choiros -- --template react-ts
npm install zustand
```

### UI Components

| Need | Package | Notes |
|------|---------|-------|
| **Rich Text Editor** | @tiptap/react | Notion-like, extensible |
| **Window Dragging** | @dnd-kit/core | Modern, accessible, flexible |
| **Terminal** | @xterm/xterm | De facto standard |
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
| **SQLite** | sql.js | SQLite compiled to WASM (optional in v0) |

```bash
npm install sql.js
```

### CSS Strategy

**Vanilla CSS with CSS Custom Properties** (not Tailwind)

Rationale:
- Full control over desktop-like aesthetics
- No build complexity
- CSS custom properties for theming
- BEM naming for component styles

---

## Backend Stack

### Control Plane

| Choice | Details |
|--------|---------|
| **Repo** | Separate app/repo (trusted) |
| **UI** | Stable, no hot reload |
| **Auth** | Owned by control plane |

### Sandboxes

| Choice | Details |
|--------|---------|
| **Provider** | Sprites (v0) |
| **Model** | Director + Associate per user |
| **Isolation** | No secrets inside sandboxes |

### Models

| Choice | Details |
|--------|---------|
| **Provider** | Bedrock (v0) |
| **Multi-provider** | Deferred (branch in progress) |

### Time Travel

| Choice | Details |
|--------|---------|
| **Git** | Checkpoints and resets via Associate tasks |

---

## Project Structure (v0)

```
choiros/
├── api/                     # Parsing backend
├── supervisor/              # Director/Associate harness (prototype)
├── choiros/                 # Vite UI
└── docs/                    # Documentation
```

---

## Key Dependencies Summary (v0)

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

---

## Deferred (post-v0)

- NATS event bus and WebSocket gateway
- Firecracker/TEE isolation
- S3/Qdrant persistence
