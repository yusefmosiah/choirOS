# Human Interrupt Lane Spec (v0.2, explicitly NOT v0 product scope)

This spec defines the “human interrupt lane”: outbound notifications (email/Slack/Telegram/etc.) and inbound human replies that can unblock or steer runs.

Important:
- This is **NOT required for v0** (headless single-player does not need it).
- It is **logically simple**, but operationally nontrivial because it adds interface surface area and security risk.
- Any interface surface takes a **string** and then compiles it into **typed inputs**. That compilation boundary is the whole point.

This spec is included now only to preserve architectural coherence.

---

## 0) Design goals

- Provide a minimal, self-hostable adapter pattern for human-in-the-loop.
- Prevent “message injection”: human replies must not be arbitrary instructions; they must compile into typed events.
- Make every human interaction replayable via receipts (event sourcing).
- Enforce safe defaults and timeouts; silence must be safe.

Non-goals:
- Turnkey hosted service. (You can vibe-code and self-host adapters.)
- Complex collaboration UX. (This is a lane, not the product.)
- Persistent agent IDs. (Runs and work items are sufficient.)

---

## 1) When this lane is used

Only in DEFERENTIAL mood (or an explicit approval sub-mode) for:
- Transformative questions that change the next action.
- Approvals for privileged actions (publish, promote, export, later signing).
- “Request review” of critical diffs/spec changes.

This lane is not used for routine status spam.

---

## 2) Outbound requests (typed, pointer-based)

Outbound messages are generated from typed request objects, not freeform prose.

### 2.1 Request types

REQUEST_QUESTION
- question_id
- question_text (single transformative question)
- default_action (what happens on timeout)
- impact (what decision it changes)
- deadline_seconds
- context_handles (hash pointers: doc/receipt IDs; never paste large blobs)
- reply_schema (allowed responses)

REQUEST_REVIEW
- review_id
- target_handles (diff hash, doc hash, run receipt hash)
- lens (security/product/correctness/clarity)
- deadline_seconds
- default_action
- reply_schema

REQUEST_APPROVAL
- approval_id
- action (e.g., PUBLISH, PROMOTE, EXPORT)
- parameters (hashed pointers)
- deadline_seconds
- default_action
- reply_schema

### 2.2 Reply schemas (bounded)

Examples:
- YES/NO
- A/B/C
- short text <= N chars (still compiled)
- numeric threshold (e.g., “max spend 50 chips”)

Reply schemas are strict to prevent arbitrary instruction injection.

---

## 3) Channel adapters (self-hostable)

Adapters deliver outbound requests and receive inbound replies.

Supported channels are implementation detail:
- email (SMTP outbound, webhook inbound or mailbox polling)
- Slack (webhook)
- Telegram (bot API)
- SMS (Twilio-like)

Each adapter must:
- deliver a human-readable message with a short reply format,
- include a signed reply token,
- and provide a webhook endpoint to receive the reply.

---

## 4) Security: signed reply tokens and no implicit authority

### 4.1 Signed reply tokens
Every outbound request includes a token that binds:
- request_id
- user_id (recipient identity)
- expiry timestamp
- allowed reply schema
- hash of request object

The inbound handler rejects:
- expired tokens
- wrong recipient
- schema-violating replies
- replayed tokens (optional nonce)

### 4.2 No implicit authority
Inbound text never becomes an instruction.
It is compiled into a typed event and then processed by policy.

---

## 5) Inbound compilation: string → typed event

Inbound replies are strings. The system compiles them into typed events:

HUMAN_REPLY_EVENT
- request_id
- channel
- sender_identity
- raw_text (stored, but not executed)
- parsed_choice (YES/NO/A/B/etc.)
- parsed_payload (bounded)
- receipt pointers (token validation, timestamps)

Compilation rules:
- strict parsing
- bounded payload sizes
- no markdown injection
- no tool calls allowed in the parsing step

---

## 6) Integration with AHDB and moods

Inbound events may update only:
- DRIVE (preferences) via explicit preference updates
- BELIEVE (constraints) if allowed by policy
- Policy decisions (approval tokens) if the request type is approval

Inbound events must not directly:
- update ASSERT
- trigger privileged syscalls without policy token checks

The director consumes HUMAN_REPLY_EVENT and decides next:
- continue run
- change mood
- split work item
- halt

---

## 7) Timeouts and safe defaults

Each request has:
- deadline_seconds
- default_action

On timeout:
- system executes default_action without waiting
- emits TIMEOUT_RECEIPT event

Default actions must be conservative:
- halt or split
- downgrade to hypothesis
- quarantine outputs
- do not publish/export

---

## 8) Replay and receipts

Every outbound and inbound interaction is event-sourced:

OUTBOUND_REQUEST_SENT
- request object hash
- channel
- recipient identity
- token hash
- timestamp

INBOUND_REPLY_RECEIVED
- request_id
- token validation receipt
- compiled HUMAN_REPLY_EVENT hash

This makes human decisions auditable and replayable.

---

## 9) Minimal implementation steps (later, not v0)

1) Define request objects and reply schemas.
2) Implement one adapter (email or Slack).
3) Implement token signing/verification.
4) Implement inbound compilation to HUMAN_REPLY_EVENT.
5) Wire director to consume events and unblock runs.
6) Add conservative defaults and rate limits.

---

## 10) Doctrine block (prompt-ready)

HUMANS ARE INTERRUPTS, NOT CO-PROCESSORS.
- OUTBOUND: TYPED REQUESTS ONLY
- INBOUND: STRING → COMPILE → TYPED EVENT
- NO IMPLICIT AUTHORITY
- TIMEOUTS ARE SAFE

DEFERENTIAL MOOD ONLY.
