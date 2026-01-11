# ChoirOS Current State

> Snapshot as of Jan 2026 — reality vs. vision for the Automatic Computer.

---

## Summary

ChoirOS is evolving into an **Automatic Computer**: a personal mainframe that runs the shell, agent, and version control inside a sandbox. The desktop works end-to-end for local dev, but deployment hardening and self-hosted CI/CD are not done yet.

---

## Component Status

### ✅ Complete / Functional
- Desktop shell + window manager (`choiros/src/components/desktop`)
- Writer + Files apps (`choiros/src/components/apps`)
- FastAPI parsing backend (`api/`)
- Supervisor runtime + agent harness (`supervisor/`)
- Git checkpoints + GitPanel UI (`supervisor/git_ops.py`, `choiros/src/components/apps/GitPanel.tsx`)

### 🔄 In Progress / Partial
- NATS plumbing (browser + supervisor clients exist, not wired)
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
4. **Security posture** — sandbox isolation and auth story for public access.

---

## Near-Term Milestone

**Build Choir inside Choir:** the desktop must be able to edit its own source, commit safely, push to CI/CD, and redeploy without leaving the app.
