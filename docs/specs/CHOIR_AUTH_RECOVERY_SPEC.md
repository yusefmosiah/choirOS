# Choir Auth + Recovery Spec
Updated: 2026-01-18
Status: DRAFT

## Scope
Define a concrete auth and recovery strategy that is secure enough to use now, with a clean path to a managed passkey service later. This spec covers flows, data model, API endpoints, and rate limits.

## Issue Alignment
- AUTH-03: Passkey auth + recovery strategy (threat model, flows, data model).
- AUTH-04: Email recovery channel integration (Resend) + verification flow.
- AUTH-05: WhatsApp + Telegram recovery channels (secure binding, opt-in, cooldowns).
- SEC-01: Security-by-design scope for chat app I/O + MCP server (capabilities, audit, isolation boundaries).

## Goals
- Provide a working local auth flow using passkeys without external services.
- Make recovery possible without making messaging channels primary auth factors.
- Preserve forward compatibility with passkey-as-a-service (drop-in backend swap).
- Establish audit and rate limiting to prevent abuse.

## Non-Goals (Phase 1)
- Full attestation chain validation or device risk scoring.
- Social or delegated recovery beyond explicitly bound channels.
- Enterprise SSO or IdP integration.

## Security Posture (Phase 1)
- Passkeys are primary auth. Messaging channels are recovery-only.
- Recovery requires explicit channel binding and multi-channel approval.
- Any recovery attempt triggers notifications to all bound channels.
- Avoid user enumeration by returning generic responses for recovery initiation.

## Data Model (SQLite)
New tables (existing tables are in `shared/auth.py`).

### auth_recovery_channels
Stores bound recovery channels for a user.
- channel_id (TEXT, PK)
- user_id (TEXT, FK)
- kind (TEXT) enum: email | whatsapp | telegram
- address (TEXT) normalized identifier (email or phone or handle)
- display_name (TEXT) optional label
- verified_at (TEXT) nullable
- created_at (TEXT)
- last_used_at (TEXT) nullable
- revoked_at (TEXT) nullable
- metadata_json (TEXT) optional

### auth_recovery_requests
Tracks active recovery sessions.
- recovery_id (TEXT, PK)
- user_id (TEXT, FK)
- status (TEXT) enum: pending | approved | expired | canceled | completed
- required_approvals (INTEGER) default 2
- expires_at (TEXT)
- created_at (TEXT)
- completed_at (TEXT) nullable
- created_ip (TEXT) nullable
- created_ua (TEXT) nullable

### auth_recovery_approvals
Approvals recorded for a recovery request.
- approval_id (TEXT, PK)
- recovery_id (TEXT, FK)
- channel_id (TEXT, FK)
- kind (TEXT) enum: email | whatsapp | telegram
- approved_at (TEXT)
- token_hash (TEXT) one-time token hash
- metadata_json (TEXT) optional

### auth_recovery_codes
One-time recovery codes provided at enrollment.
- code_id (TEXT, PK)
- user_id (TEXT, FK)
- code_hash (TEXT)
- created_at (TEXT)
- used_at (TEXT) nullable

### auth_audit_events
Security audit trail.
- event_id (TEXT, PK)
- user_id (TEXT)
- event_type (TEXT) enum: auth_passkey_add | auth_passkey_remove | auth_recovery_start | auth_recovery_approve | auth_recovery_complete | auth_channel_bind | auth_channel_revoke | auth_session_create | auth_session_revoke
- created_at (TEXT)
- ip (TEXT) nullable
- user_agent (TEXT) nullable
- metadata_json (TEXT) optional

## Flows

### 1) Passkey Registration (Primary Auth)
1. Client requests registration options.
2. Server creates challenge and returns `publicKey` options.
3. Client completes WebAuthn ceremony.
4. Server verifies and stores credential (Phase 1: minimal verification, Phase 2: full crypto).
5. Server creates session and returns token.

Notes:
- Phase 1 can accept the stub flow but must store enough fields to move to full verification.
- Store `credential_id`, `public_key`, `sign_count`, `transports`, `aaguid` (if provided), `client_label`.

### 2) Passkey Authentication
1. Client requests authentication options.
2. Server returns challenge + allowCredentials.
3. Client completes WebAuthn assertion.
4. Server verifies assertion and creates session.

### 3) Channel Binding (Email/WhatsApp/Telegram)
1. Authenticated user initiates channel bind (email/phone/handle).
2. Server issues a verification challenge token with short TTL.
3. Server sends verification to channel (email link or OTP).
4. User submits token/OTP to verify; channel is marked verified.

Restrictions:
- Channel binding requires an active session.
- Channel verification links expire quickly (10-15 minutes).

### 4) Recovery Initiation (Non-Enumerating)
1. User submits an identifier (user_id or email) to start recovery.
2. Server returns 202 with generic response.
3. If user exists and has bound channels, server creates recovery request and sends approval challenges to channels.

### 5) Recovery Approval (2-of-3)
1. User responds to challenges in two distinct channels.
2. Each approval posts to `/recovery/approve` with token.
3. When approvals >= required_approvals, recovery is marked approved.
4. Server issues a short-lived recovery completion token.

### 6) Recovery Completion
1. Client submits completion token.
2. Server revokes all active sessions.
3. Server creates a new session and returns token.
4. Client must register a new passkey or confirm existing passkeys.

### 7) Recovery Codes (Last Resort)
- Codes are shown once at enrollment.
- If no channels can be verified, a valid recovery code + email approval can allow completion.

## API Endpoints (Proposed)
Note: These extend the existing `/passkeys/*` and `/sessions/*` endpoints in `api/routers/auth.py`.

### Passkeys
- POST `/passkeys/register/options`
- POST `/passkeys/register/verify`
- POST `/passkeys/authenticate/options`
- POST `/passkeys/authenticate/verify`

### Sessions
- GET `/sessions`
- POST `/sessions/revoke`

### Channels
- POST `/recovery/channels/bind`
  - body: { kind, address, display_name? }
  - returns: { channel_id, status: "pending" }
- POST `/recovery/channels/verify`
  - body: { channel_id, token }
  - returns: { verified: true }
- GET `/recovery/channels`
  - returns: list of bound channels (mask identifiers)
- POST `/recovery/channels/revoke`
  - body: { channel_id }

### Recovery
- POST `/recovery/start`
  - body: { identifier }
  - returns: { status: "ok" } (always 202)
- POST `/recovery/approve`
  - body: { recovery_id, token }
  - returns: { approved: true, remaining_approvals }
- POST `/recovery/complete`
  - body: { recovery_id, completion_token }
  - returns: { session, token }

### Recovery Codes
- POST `/recovery/codes/issue`
  - body: {} (auth required)
  - returns: { codes: [ ... ] } (shown once)
- POST `/recovery/codes/verify`
  - body: { recovery_id, code }
  - returns: { approved: true, remaining_approvals }

### Audit (Optional Phase 2)
- GET `/audit/auth` (admin only)

## Rate Limits (Suggested Defaults)
Apply per IP + per user_id (where applicable). Store counters in-memory first, move to Redis later.

- Passkey registration options: 5/min per user_id, 30/min per IP.
- Passkey registration verify: 10/min per user_id, 60/min per IP.
- Passkey auth options: 10/min per user_id, 60/min per IP.
- Passkey auth verify: 20/min per user_id, 120/min per IP.
- Channel bind: 3/hour per user_id, 10/hour per IP.
- Channel verify: 10/hour per user_id, 30/hour per IP.
- Recovery start: 3/hour per identifier, 20/hour per IP.
- Recovery approve: 10/hour per recovery_id, 50/hour per IP.
- Recovery complete: 5/hour per recovery_id, 20/hour per IP.
- Recovery code issue: 1/day per user_id.

Lockout rules:
- 5 consecutive failed approvals -> cooldown 15 minutes.
- 10 failed passkey assertions -> cooldown 30 minutes.

## Forward Compatibility (Passkey Service)
- Store raw WebAuthn fields so a managed service can be dropped in later.
- Keep an `AuthProvider` interface that can swap between local WebAuthn and external service.

## Security-by-Design Notes (SEC-01)
- Chat I/O and MCP server must use capability-scoped tokens derived from authenticated sessions.
- Commands executed via chat must be auditable and bound to a verified user identity.
- Recovery flows should invalidate any long-lived chat/MCP tokens.

## Open Questions
- Should recovery require a manual hold (e.g., 15 min delay) before completion?
- Should we require passkey re-verification before revoking existing passkeys?
- Do we allow email-only recovery for bootstrap accounts, and under what limits?
