# Architecture Research Roadmap (v0)
Status: ACTIVE
Date: 2026-01-18
Owner: ChoirOS Core

## Purpose
Provide a concrete agenda for the upcoming deep research + review session so the next build steps are unambiguous.

## Current state (local)
- Supervisor + API + frontend run locally.
- Event contract, AHDB projection, run/work items, verifier plan/runner, mood engine,
  and run orchestration are implemented.
- Fast unit suite and EventStream E2E are green.

## Research goals (next session)
1) Platform architecture decisions (local -> sandbox -> platform)
2) Auth gateway and identity propagation
3) NATS tenancy model (per-user subjects vs per-tenant streams)
4) Sandbox and isolation model (worktree + container + network policy)
5) Build and deployment pipeline for self-rebuild

## Questions to answer (with sources)
### A) Auth and gateway
- What is the minimal gateway stack for our needs (OIDC/JWT)?
- Where do we verify tokens: gateway only, supervisor too, or both?
- How do we map identity -> user_id -> NATS subject permissions?

### B) NATS as platform service
- Recommended multi-tenant patterns (accounts, exports/imports, subject permissions).
- JetStream stream layout: per-tenant vs shared stream.
- Cost and ops tradeoffs for shared cluster vs per-tenant NATS.

### C) Sandboxes and execution
- Best practice for per-run ephemeral workspaces (worktrees + containers).
- Network egress controls for verifier lane vs execution lane.
- Artifact storage: local filesystem now, object store later.

### D) Build + deploy
- CI plan for verifier suites and E2E.
- Image build pipeline for supervisor + frontend.
- Secrets and config management in sandboxes.

## Output of the research session
- A platform architecture diagram (local -> sandbox -> platform)
- A phased rollout plan with milestones
- A list of decisions + chosen defaults (and why)
- A backlog of implementation tasks aligned to the SD-* bootstrap sequence

## Immediate follow-up tasks (post research)
- Add auth gateway stub + token verification middleware. (DONE 2026-01-18)
- Add NATS auth configuration with per-user subject prefix. (DONE 2026-01-18)
- Add sandbox runner interface (even if local-only at first). (DONE 2026-01-18)
- Standardize dev entrypoint for consistent setup. (IN PROGRESS)

## Phase 0 decisions (2026-01-18)
- Shared NATS cluster with per-user subject permissions.
- Browser clients are subscribe-only; JetStream APIs reserved for supervisor.
- Auth gateway issues per-session NATS credentials (static for now).
