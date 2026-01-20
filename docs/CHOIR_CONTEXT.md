# Choir Overview (Vision + Context)

Choir (ChoirOS) is an **automatic computer**: a web desktop OS that runs autonomous work
loops (coding, research, audits) inside strict sandbox boundaries, with mechanical
version control and explicit verification. The point is not to make agents talk more,
but to make autonomous work **reliable, reversible, and accountable**. Progress is
measured in verified state changes, not chat output.

This is the missing layer between "one-off agents" and "trustworthy automation." Choir
turns agentic work into a system with memory, policy, receipts, and rollback.

## Why It Exists
Modern AI can do useful work but cannot be trusted to change real systems without guard
rails. Choir is built to make autonomy *boring* in the best way: verifiable, safe, and
recoverable. You should be able to leave it running, come back, and see exactly what
changed, why it changed, and whether it was verified.

## Core Thesis
Autonomy becomes safe when it is **bounded by policy** and **validated by evidence**.
Therefore:
- Every action is gated by capabilities (what is allowed).
- Every claim is gated by verification (what is true).
- Every change is reversible (what can be undone).

## Product Shape (Vision)
- **Web desktop** as the primary interface: a workspace with apps, files, and a run
  console.
- **Sandboxed execution**: work runs in isolated environments that can be reset on
  failure.
- **Director control plane**: policy engine that selects capability profiles (moods),
  sets budgets, and gates commits.
- **Verification green threads**: structured checks that produce attestations, not
  vibes.
- **Event bus + knowledge state**: typed events update the state vector (AHDB), not
  free-form narration.

In short: a run emits artifacts and attestations; the director decides whether code
lands in the workspace based on verifier receipts and policy.

## Non-Negotiable Invariants
- Failed runs leave no code: changes are transactional.
- No verifier -> no assert: behavioral claims require receipts/attestations.
- Notes are events; code is git: telemetry is append-only, source stays clean.
- Publish is explicit: private work never becomes global by accident.
- Local and global epistemics stay separated by policy gates.

## Epistemics and Authority
Choir treats knowledge like a system, not a chat log. Assertions can only cite promoted
evidence. Hypotheses are explicit. Attestations are structured and typed. This prevents
context poisoning and forces real accountability.

## Web-First, Social-Optional
Choir is a web desktop with sandboxed execution. Today the dev stack still runs locally,
but the target shape is web-first and multi-sandboxed.

The social layer is optional and explicit: users can **publish** artifacts, others can
**promote** and **attest**, and only promoted evidence can be **asserted** globally. This
preserves safety while enabling a future market for trustworthy knowledge.

## What Choir Is Not
- Not a chatbot.
- Not "run 30 agents and pick the best."
- Not a plugin pile.
- Not "summarize everything into markdown."

Choir compiles untrusted reality into asserted state through verifiers, receipts, and
guarded transitions.

## Use This When Discussing Features
Assume web-desktop + sandboxed execution, explicit verification, and strict publish
boundaries. If a proposal weakens these invariants, it needs a compelling safety story
or it does not fit Choir.
