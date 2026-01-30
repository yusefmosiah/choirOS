# Experiment: q4-context-assembly

**Date**: 2026-01-29T01:32:01.269745Z
**Question**: How should AHDB be assembled into worker context?

## PREDICTION
Ranking AHDB entries against task descriptions reduces context size while preserving task-relevant keys.

## EXPERIMENT
Score AHDB keys against sample tasks using token overlap and measure size reduction plus hit-rate for expected keys (synthetic data if AHDB is empty).

## OBSERVE
If size reduction exceeds 50% and hit-rate exceeds 80%, support ranking as a viable assembly heuristic (LLM performance still untested).

## LEARNING
- Status: inconclusive
- Summary: Ranking reduces context size and retrieves expected keys for most tasks, but LLM performance remains untested.
- Evidence: synthetic
