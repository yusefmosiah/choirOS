# NATS Phase 0 Hardening (v0)
Status: ACTIVE
Date: 2026-01-18
Owner: ChoirOS Core

## Goal
Share a single NATS cluster across users while enforcing subject isolation and reducing client blast radius.

## Decisions (Phase 0)
- Shared NATS cluster with per-user subject permissions.
- Browser clients are **subscribe-only** and do **not** use JetStream APIs.
- Supervisor is the only publisher + JetStream manager.
- Auth gateway issues NATS credentials bound to a session.

## Credential Flow
1) User signs in (passkey stub) → session token.
2) Client calls `GET /api/auth/nats/credentials` with the session token.
3) API returns NATS WebSocket URL + per-user credentials and subject prefix.
4) Frontend connects to NATS using those credentials and subscribes to the returned subject prefix.

## Current Config
- `config/tenancy.json` maps user → NATS web credentials + subject prefix.
- `config/nats.conf` defines:
  - `choiros_local_web` (subscribe only to `choiros.local.>`)
  - `choiros_supervisor` (publish/subscribe to `choiros.>` + `$JS.API.>`)
- Supervisor uses `NATS_USER`/`NATS_PASSWORD` to publish + manage JetStream.
  - Defaults are set in `dev.sh` and `scripts/test.sh`.
- NATS CLI example (publish as supervisor):
  - `nats --user choiros_supervisor --password local_supervisor pub choiros.local.system.note.status '{...}'`

## Client Behavior
- Browser connects using per-user credentials returned by the auth gateway.
- `choiros/src/lib/nats.ts` does **not** call JetStream APIs.
- `publishEvent()` exists but will fail with read-only credentials.
- You must sign in (Auth app) to receive NATS credentials in local dev.

## Known Gaps (Phase 0)
- WebAuthn verification is stubbed (no cryptographic checks).
- NATS credentials are static (not rotated per session).
- Multi-user auth is not enforced across all supervisor HTTP endpoints yet.

## Next Steps (Phase 1)
- Issue **short-lived** NATS credentials per session.
- Move to multi-account NATS (per-tenant) for stronger isolation.
- Add server-side fanout (SSE/WS) so browsers never touch NATS directly.
