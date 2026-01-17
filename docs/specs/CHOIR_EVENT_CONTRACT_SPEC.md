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

## Canonical event types (v0)
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
