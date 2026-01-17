# Choir Event Contract (v0)
Status: DRAFT
Date: 2026-01-17
Owner: ChoirOS Core

## Decision summary
This document is the canonical contract for NATS subjects, event naming, and stream configuration.

- Subject format: `choiros.{user_id}.{source}.{event_type}`
- Event type format: lower-case, dot-delimited (e.g., `file.write`)
- Stream naming: single JetStream stream named `CHOIR` with subjects `choiros.>`

## Event schema
All events must follow this shape:

- id: string (UUID)
- timestamp: number (Unix ms)
- user_id: string
- source: `user` | `agent` | `system`
- event_type: string (dot-delimited, lower-case)
- payload: object (event-specific)

## Event type normalization
- Canonical event types are lower-case and dot-delimited.
- Legacy separators are normalized: `/` → `.`, `_` → `.`
- NOTE subtypes normalize as `note.<kind>` (e.g., `NOTE/REQUEST_VERIFY` → `note.request.verify`)
- RECEIPT subtypes normalize as `receipt.<kind>` via either `RECEIPT/<KIND>` or `<KIND>_RECEIPT`

## Canonical event types (v0)
Core events:
- file.write
- file.delete
- file.move
- message
- tool.call
- tool.result
- window.open
- window.close
- checkpoint
- undo

Notes (AHDB-typed telemetry):
- note.observation
- note.hypothesis
- note.hyperthesis
- note.conjecture
- note.status
- note.request.help
- note.request.verify

Receipts (capabilities + verification):
- receipt.read
- receipt.patch
- receipt.verifier
- receipt.net
- receipt.db
- receipt.export
- receipt.publish
- receipt.context.footprint
- receipt.verifier.results
- receipt.verifier.attestations
- receipt.discrepancy.report
- receipt.commit
- receipt.ahdb.delta
- receipt.evidence.set.hash
- receipt.retrieval
- receipt.conjecture.set
- receipt.policy.decision.tokens
- receipt.security.attestations
- receipt.hyperthesis.delta
- receipt.expansion.plan
- receipt.projection.rebuild
- receipt.attack.report
- receipt.disclosure.objects
- receipt.mitigation.proposals
- receipt.preference.decision
- receipt.timeout

## Examples

Subject for a user file write:
`choiros.local.user.file.write`

Event example:
```
{
  "id": "0d1b6c0e-6f41-4f1c-8f37-3a0f9f7b2e66",
  "timestamp": 1737072000000,
  "user_id": "local",
  "source": "user",
  "event_type": "file.write",
  "payload": {
    "path": "docs/notes.md",
    "bytes": 128
  }
}
```

## Notes
- Stream retention and storage policy are implementation details; the stream name and subject pattern are not.
- If a legacy source uses uppercase or underscores, normalize to the dot-delimited format before publishing.
