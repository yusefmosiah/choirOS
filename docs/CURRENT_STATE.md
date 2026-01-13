# ChoirOS Current State

> Snapshot as of Jan 2026 — reality vs. vision for the Automatic Computer.

---

## Summary

ChoirOS is evolving into an **Automatic Computer** with two sandboxes per user: a Director loop and an Associate loop. The desktop works end-to-end for local dev, but dual-sandbox orchestration and control-plane separation are not implemented yet.

---

## Component Status

### ✅ Complete / Functional
- Desktop shell + window manager (`choiros/src/components/desktop`)
- Writer + Files apps (`choiros/src/components/apps`)
- FastAPI parsing backend (`api/`)
- Supervisor runtime + agent harness (`supervisor/`) [prototype]
- Git checkpoints + GitPanel UI (`supervisor/git_ops.py`, `choiros/src/components/apps/GitPanel.tsx`)

### 🔄 In Progress / Partial
- Director/Associate dual-sandbox orchestration
- Sprites sandbox adapter
- EventStream UI (ready, needs live events)
- In-app deploy loop (git push → CI/CD → redeploy)

### 🚧 Stubs / Demos
- Mail app UI (sample data only)
- MeadowPopup demo component
- Terminal app (not implemented)

---

## Deployment Gaps (Blocking)

1. **Version control safety** — guardrails around `git reset --hard`, ignore generated files, and audit checkpoint content.
2. **CI/CD loop** — push from inside Choir and surface build/deploy status in the UI.
3. **Event stream** — real NATS wiring to replace local-only events.
4. **Security posture** — control-plane separation and sandbox isolation.

---

## Near-Term Milestone

**Director + Associate:** dual sandboxes with Ralph loops and git time travel.
