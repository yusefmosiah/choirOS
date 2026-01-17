# Choir Capabilities (Syscalls) Spec (v0)

This document defines **CAPABILITIES**: the syscall surface of the automatic computer. Capabilities define what can happen, under what constraints, with what receipts. They are enforced by the director (policy engine) and the mood state machine.

Doctrines define what counts; capabilities define what can happen.

## 0) Capability model

A capability is granted via a time-bounded lease:

CAPABILITY_LEASE :=
- lease_id (content-addressed)
- principal (run_id, user_id, mood)
- syscall_class (READ/WRITE/VERIFY/NET/DB/EXPORT/PUBLISH/PROMOTE/…)
- scope (paths/domains/tables)
- duration (TTL + idle timeout)
- budget (max calls/bytes/tokens/cost)
- constraints (no arbitrary headers, no raw creds, no copy limits)
- revocation (director can revoke instantly)
- receipts required on each use

Sessions cannot execute privileged actions directly. They emit typed requests; the director grants or refuses leases.

## 1) Syscall classes (v0)

### 1.1 READ (I/O)
- READ_FILE(path, max_bytes)
- READ_DIR(path, depth, filters)
- READ_OBJECT(hash)
- READ_RECEIPT(id)

Constraints:
- scope-limited by lease
- reads are side effects; must be logged
- raw content never becomes authority without promotion/attestation

Receipts:
- ReadReceipt(path/hash, bytes, timestamp, lease_id)

### 1.2 WRITE (workspace)
- WRITE_FILE(path, content_hash)
- APPLY_PATCH(patch_hash)
- CREATE_WORKTREE(run_id)
- DISCARD_WORKTREE(run_id)

Constraints:
- only in allowed moods (CALM/BOLD)
- always in ephemeral worktree for a RUN
- must be followed by verification before commit eligibility

Receipts:
- PatchReceipt(diff_hash, files_touched, lease_id)

### 1.3 VERIFY (green thread)
- RUN_VERIFIER(command_spec)
- STORE_VERIFIER_OUTPUT(artifact_hash)
- EMIT_ATTESTATION(attestation_hash)

Constraints:
- runs in isolated verifier lane
- raw outputs stored as artifacts only
- structured reports + attestations emitted

Receipts:
- VerifierReceipt(command, artifact_hash, versions)

### 1.4 NET (egress)
- NET_REQUEST(dest, method, body_ref, purpose)

Constraints:
- never allow raw curl
- identity-bound auth only (no user-supplied Authorization headers)
- allowlisted destinations per mood
- default off outside CURIOUS (and limited PARANOID)

Receipts:
- NetReceipt(dest, bytes_out, bytes_in, lease_id)

### 1.5 DB (query)
- DB_QUERY_REQUEST(intent, schema_expected, constraints)
- DB_QUERY_EXECUTE(query_plan)  (DB-expert lane only)

Constraints:
- general sessions may not execute queries
- DB-expert verifier lane executes under strict scope/row/time limits
- results are typed and bounded; raw dumps stored as artifacts

Receipts:
- DbReceipt(db_snapshot, rows_returned, lease_id)

### 1.6 EXPORT (data egress)
- EXPORT_OBJECT(object_hash, destination_handle)

Constraints:
- privileged
- requires DEFERENTIAL approval or policy token
- never combines local reads + network + creds in one lane

Receipts:
- ExportReceipt(destination, object_hash)

### 1.7 PUBLISH (local → public)
- PUBLISH_OBJECT(object_hash, visibility, redaction_policy)

Constraints:
- explicit user action or explicit policy token
- creates a public candidate; does not grant assertion

Receipts:
- PublishReceipt(object_hash, visibility)

### 1.8 PROMOTE / CHALLENGE (social, later)
- PROMOTE_ATOM(atom_hash, stake)
- CHALLENGE_ATOM(atom_hash, stake, counterevidence)

Constraints:
- outside v0, but interfaces should exist as stubs
- promotion is voluntary; challenges are permissionless
- produces promotion state transitions and receipts

## 2) Mood × capability matrix (minimal)

CALM:
- READ/WRITE (worktree scoped), VERIFY (request), no NET/DB/EXPORT/PUBLISH by default

CURIOUS:
- READ (repo), NET (allowlisted), KB search via verifier lane, no WRITE by default

SKEPTICAL:
- VERIFY required, limited WRITE for fixes, no NET by default

PARANOID:
- VERIFY + policy gates, minimal READ/WRITE, strict NET off unless identity-bound checks

CONTRITE:
- READ receipts/events, rebuild projections; no side effects

DEFERENTIAL:
- can request human interrupt lane; can request privileged approvals

(Full mood profiles in CHOIR_MOODS_SPEC.md.)

## 3) Requests and refusals

Sessions emit typed requests:
- CAPABILITY_REQUEST(syscall_class, scope, budget, reason)
- DB_QUERY_REQUEST / VERIFY_REQUEST / PUBLISH_REQUEST

Director returns:
- GRANT(lease_id)
- REFUSE(reason_code, safer_alternative)

All requests and decisions are event-sourced.

## 4) Receipts and content addressing

All capability uses must emit receipts.
All receipt-bearing objects must be content-addressed and referenced by hash in events.
