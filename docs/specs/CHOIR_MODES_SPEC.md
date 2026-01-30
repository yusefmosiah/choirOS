# Choir Modes Specification
Status: DRAFT
Date: 2026-01-30
Owner: ChoirOS Core

## Summary
Choir modes are deterministic, capability-bounded configurations that gate tool access,
network access, and resource budgets for a run. The Machine selects an initial mode
based on AHDB state and the prompt, then emits mode start/update/stop events to
drive runtime behavior.

## Mode catalog
- CALM: Default execution mode with standard budgets and allowlists.
- SKEPTICAL: Verification-heavy mode used when risk is elevated or verifiers fail.
- BOLD: High-initiative mode with broader tool access when time is critical.
- CURIOUS: Exploration mode that prioritizes investigation and hypothesis formation.
- CONTRITE: Constrained recovery mode after errors or regressions.
- DEFERENTIAL: Low-risk, user-confirming mode for ambiguous or high-stakes tasks.
- PARANOID: Strict isolation and minimal tool access for sensitive paths.
- PETTY: Narrow, repetitive execution mode for small, well-scoped follow-ups.

## Configuration source of truth
- Runtime configuration lives in `supervisor/mode_config.py` and `supervisor/mode_engine.py`.
- Mode selection uses AHDB signals (e.g., crash_detected, repeated_verifier_failures).
- Budgets include time_seconds, tool_calls, diff_bytes, and files_touched.

## Event contract
- `mode.start` opens a mode for a run (includes allow_write and prompt).
- `mode.update` communicates status transitions.
- `mode.stop` ends the mode with final status.

## Open questions
- Formalize per-mode verifier requirements.
- Map mode transitions to user-visible UI markers.
