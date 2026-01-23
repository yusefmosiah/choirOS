# Choir AgentFS Integration Spec (v0)
Status: DRAFT
Date: 2026-01-23
Owner: ChoirOS Core

## Decision summary
- AgentFS is the canonical filesystem state for Choir.
- Sprites is a temporary execution substrate; AgentFS remains the source of truth.
- Session naming default: per-workspace.
- AgentFS DBs live under `.context/agentfs/`.
- Alpha risk accepted for now.

## Goals
- Durable sandbox filesystem across restarts.
- Portable, auditable state via single SQLite DB per session.
- Ability to migrate off Sprites to managed microVMs without data loss.

## Non-goals (v0)
- Multi-tenant, globally shared filesystems.
- Full remote replication semantics (beyond snapshot sync).

## Canonical state
- AgentFS DB is authoritative for sandbox files.
- Git remains authoritative for repo source code.
- Event log (NATS/SQLite projection) is authoritative for receipts/notes/decisions.

## Session naming
Default: per workspace
- `agentfs:<user_id>:workspace`
Optional: per-run snapshots
- `agentfs:<user_id>:workspace:run:<run_id>` (if needed)

## Storage location
- `.context/agentfs/<session>.db`
- Excluded from git via `.gitignore`.

## Local execution
- Local sandbox runner uses AgentFS session as filesystem.
- All file operations occur within AgentFS mount (e.g., `/agent`).
- On restart, re-open the same session to restore state.

## Sprites execution (temporary)
- Prior to run: sync AgentFS DB → Sprites filesystem.
- After run: sync Sprites filesystem → AgentFS DB.
- AgentFS remains canonical; Sprites is a waypoint.

## Migration path
- When moving to managed microVMs, mount AgentFS session DBs into microVMs.
- The Machine continues to operate against the same session ID.

## Risk notes
- AgentFS is alpha; treat as dev/proto for now.
- Require explicit backup/export of AgentFS DBs.

## Success criteria
- Restart preserves sandbox state.
- AgentFS DB can reconstruct sandbox filesystem deterministically.
- Sprites runs do not corrupt canonical AgentFS state.
