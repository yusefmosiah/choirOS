# Ralph-in-Ralph Master Checklist

A sequencing checklist for implementing the Director/Associate system in
successive, scoped agent runs. Each run should produce a durable artifact in
repo and leave the system in a verified, resumable state.

## Run 0: Align docs + invariants (no code)
- [ ] Confirm the invariants + threat model (ground truth on disk, evidence-only
      memory, Director is verifier-of-record).
- [ ] Decide canonical locations/names for new docs + schemas.
- [ ] Update Phase 3 docs to include wrappers, schemas, validators, evidence.
- [ ] Record open questions + decisions.

**Exit criteria:** Updated docs + a single “source of truth” checklist.

## Run 1: Repo scaffolding + empty schemas
- [ ] Create canonical folders (tasks/, evidence/, skills/, workflows/, tools/).
- [ ] Add placeholders for:
      - tasks/schema.json
      - evidence/manifest.schema.json
      - skills/skill_manifest.schema.json
- [ ] Add minimal README for each folder describing purpose + ownership.

**Exit criteria:** Directories and placeholder schemas committed.

## Run 2: Task contract schema + validator
- [ ] Define task contract schema (objective, scope, constraints, verify,
      budgets, escalation, risk posture, merge policy).
- [ ] Implement validate_task.py (hard-fail on invalid contracts).
- [ ] Add sample task contract (T-001) to prove schema works.

**Exit criteria:** Task schema validated by tool + sample contract stored.

## Run 3: Evidence bundle schema + validator
- [ ] Define evidence manifest schema (summary, checks, provenance, diffs).
- [ ] Implement validate_evidence.py.
- [ ] Add sample evidence bundle (T-001/run-001) with stub logs.

**Exit criteria:** Evidence schema validated by tool + sample bundle stored.

## Run 4: Associate wrapper (single-run, no Director)
- [ ] Implement associate_loop wrapper (shell/python).
- [ ] Enforce: budgets, tool allowlist, scope enforcement, circuit breakers.
- [ ] Require evidence bundle on proposed_done.
- [ ] Persist outputs under evidence/ and run validation.

**Exit criteria:** Human-authored task contract can drive one Associate run that
produces validated evidence.

## Run 5: Policy enforcement + system charter
- [ ] Add SYSTEM.md with invariants and operating rules.
- [ ] Add POLICY.yaml with tool permissions, external endpoints, redaction.
- [ ] Wire policy checks into associate_loop.

**Exit criteria:** Wrapper rejects tasks violating policy or scope.

## Run 6: Director wrapper (advisory mode)
- [ ] Implement director_loop that reads task contracts + evidence manifests.
- [ ] Emit next actions (spawn associate, request skill, revise task).
- [ ] Director remains non-merging and advisory-only.

**Exit criteria:** Director can be run on a task directory and emits a plan.

## Run 7: Skills scaffolding + runner
- [ ] Define skill manifest + I/O schema.
- [ ] Implement skill_runner.py enforcing policy + schema validation.
- [ ] Seed reviewer + QA skills (basic outputs only).

**Exit criteria:** Skills produce versioned bundles and validate.

## Run 8: Integration runner + merge gating
- [ ] Add integration runner that merges branches into integration branch.
- [ ] Run task verification suite + create integration evidence bundle.
- [ ] Director uses evidence + risk posture to accept/merge.

**Exit criteria:** Director can auto-merge only when evidence validates.

## Run 9: Parallel associates + orchestration
- [ ] Add multi-associate spawning with disjoint scopes.
- [ ] Add integration step for conflict resolution.
- [ ] Optional DAG workflow runner + state.json.

**Exit criteria:** Parallel runs produce merged, validated evidence.

## Run 10: Evaluation harness + metrics logging
- [ ] Add eval scenarios + harness for canned tasks.
- [ ] Log metrics (time-to-green, iterations-to-green, rework rate, etc.).
- [ ] Produce dashboard-ready JSON summaries.

**Exit criteria:** System can be evaluated and compared across runs.

## Notes for sequencing
- Keep each run scoped to 1–3 files whenever possible.
- Always validate schemas after edits.
- Avoid adding external services until schemas + wrappers are stable.
