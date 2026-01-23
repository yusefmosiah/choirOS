# Choir Work Queue Spec (v0)
Status: DRAFT
Date: 2026-01-23
Owner: ChoirOS Core

## Decision summary
The command bar must remain responsive. User actions enqueue work items; the Machine schedules Mode execution from the queue without blocking UI. The Machine is the outer control plane and does not perform research or tool use directly.

## Goals
- Command bar never blocks while work is running.
- Multiple work items can be queued and scheduled deterministically.
- Single-writer rule enforced: only one write-capable Mode at a time.
- Read-only Modes may run concurrently.
- Queue state is durable across restarts (event-sourced).

## Non-goals (v0)
- Preemptive multi-writer concurrency.
- Fairness across multiple human users.
- Global distribution or load balancing.

## Definitions
- Work item: a single objective the Machine can schedule into a Mode.
- Queue: persistent list of work items with status and priority.
- Scheduler: Machine logic that selects the next runnable work item.

## Work item schema
Required fields:
- id
- description
- created_at
- status: queued | running | done | failed | cancelled

Optional fields:
- requested_mode
- allow_write
- priority (default: normal)
- dependencies
- risk_tier

## Queue behavior
- UI enqueues work items immediately; the command bar returns.
- Machine picks the next runnable work item when:
  - no write-capable Mode is active, or
  - the work item is read-only and there is read-only capacity.
- If a work item fails, status is updated; retries are explicit.

## Scheduling rules (v0)
1) Enforce single-writer.
2) Prefer higher priority items.
3) Respect dependencies.
4) Avoid starvation (simple FIFO within priority buckets).

## Events
- note.request.help (UI enqueue)
- mode.start / mode.stop / mode.update
- receipt.mode.transition
- receipt.commit (if applicable)

## UI requirements
- Command bar stays interactive.
- Queue indicator shows length + running items.
- User can cancel queued items.

## Success criteria
- A user can enqueue multiple commands without blocking.
- The Machine drains the queue and updates statuses.
- Restarts preserve queue state.
