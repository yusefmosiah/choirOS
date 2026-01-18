# Choir Storage + Rollback Spec (Base + Overlay)
Updated: 2026-01-18
Status: DRAFT

## Scope
Define a base + overlay storage model for user-customizable frontends running inside sprites. Map this to VC-01 (version control primitives) and SBX-01 (sandbox lifecycle + snapshot/restore).

## Goals
- Keep a single canonical base app while allowing per-user customizations.
- Support deterministic rehydration of a user workspace in a fresh sprite.
- Provide rollback on verifier failure with minimal data loss.
- Avoid a single monolithic repo containing all user changes.

## Non-Goals (Phase 1)
- Cross-user merge tooling.
- Advanced conflict resolution UI.
- Multi-region replication.

## Architecture Overview
- Base app: a canonical git repo + commit SHA (immutable once published).
- Overlay: per-user delta stored as a commit, patch, or bundle.
- Sprite workspace: a materialized filesystem of base + overlay.

Rehydration = checkout base + apply overlay.

## Storage Model

### Base
- `base_repo`: canonical git repo for the React app.
- `base_ref`: commit SHA tagged as a release (e.g., `base@2026-01-18`).
- Immutable once referenced by overlays.

### Overlay (per user)
Two supported formats (choose one as default):

Option A (recommended): Per-user git repo
- `overlay_repo` per user.
- `overlay_ref` = commit SHA.
- Pros: built-in diff/history, easy rollback, content-addressed.

Option B: Content-addressed bundle
- `overlay_blob` = tar/patch bundle keyed by hash (CAS).
- `overlay_ref` = hash + metadata.
- Pros: dedupe; no git overhead.
- Cons: need tooling for diff/history.

### Metadata (Auth/DB)
- `user_id`
- `base_ref`
- `overlay_ref`
- `last_verified_overlay_ref`
- `last_good_overlay_ref`
- `created_at`, `updated_at`

## Sprite Materialization
1. Create or restore sprite.
2. Populate workspace:
   - Fetch base repo at `base_ref`.
   - Apply `overlay_ref` (git merge/cherry-pick or patch apply).
3. Start dev/build server inside sprite.

### Checkpoints
- Use sprite checkpoints for environment + filesystem speedups.
- Do not rely on checkpoints as the source of truth for code state.
- Code source of truth is base + overlay in storage.

## Verification + Rollback

### Verification pipeline
1. User edits inside sprite.
2. Verifier runs against sprite workspace.
3. On pass: create new overlay_ref and mark as `last_verified_overlay_ref`.
4. On fail: revert workspace to `last_good_overlay_ref` and restart app.

### Rollback policy
- `last_good_overlay_ref` is updated only after pass.
- `overlay_ref` can be updated optimistically but reverted on failure.
- Store failure events for audit.

## Diffing
- Diff between overlay versions using git (Option A) or stored patch diffs (Option B).
- Diff between base and overlay for auditing what user changed.

## Mapping to VC-01
VC-01 requires: checkpoint, diff, rollback primitives.
- Checkpoint: `overlay_ref` creation at verification.
- Diff: git diff between overlay refs or overlay vs base.
- Rollback: reset workspace to `last_good_overlay_ref` and restart.

## Mapping to SBX-01
SBX-01 requires: lifecycle + snapshot/restore hooks.
- Lifecycle: create sprite, restore checkpoint, start services.
- Snapshot/restore: sprite checkpoint for speed; always reconcile to base+overlay refs on boot.
- Isolation: per-user sprite namespace + scoped network policy.

## Operational Notes
- Base updates require migration path: either rebase overlays or pin users to old base until they opt in.
- Overlay size limits prevent abuse.
- Retention: keep last N overlays per user (e.g., 20) plus last_good.

## Open Questions
- Do we allow overlays to include dependency changes (package.json)?
- Do we allow file deletions across base boundaries?
- Should overlays be signed to prevent tampering?

## Rehydration Flow (Sequence)
1. Supervisor selects `user_id` and fetches `base_ref`, `overlay_ref`, `last_good_overlay_ref`.
2. Ensure sprite exists; if not, create sprite with network policy + resource limits.
3. Attempt fast path: restore latest sprite checkpoint.
4. Reconcile filesystem to `base_ref` + `overlay_ref`:
   - Fetch base repo at `base_ref`.
   - Apply overlay (git or patch) onto workspace.
   - If apply fails, fallback to `last_good_overlay_ref`.
5. Start frontend process in sprite (dev server or production build).
6. Health check from control plane; if unhealthy, rollback to `last_good_overlay_ref` and restart.
7. Persist a new sprite checkpoint after successful start.

## Rollback Flow (On Verification Failure)
1. Verifier marks run as failed.
2. Supervisor sets `overlay_ref` back to `last_good_overlay_ref`.
3. Reset workspace inside sprite to base + `last_good_overlay_ref`.
4. Restart frontend process and notify user.
5. Record audit event and attach verifier logs to run record.
