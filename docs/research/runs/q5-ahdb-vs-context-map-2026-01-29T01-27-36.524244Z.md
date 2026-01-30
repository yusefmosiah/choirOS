# Experiment: q5-ahdb-vs-context-map

**Date**: 2026-01-29T01:27:36.524244Z
**Question**: What is the relationship between AHDB and the Context Map?

## PREDICTION
AHDB assertions will not appear directly in the context heatmap, indicating separate schemas rather than a single representation.

## EXPERIMENT
Create an AHDB delta in a temp EventStore, build a context heatmap, and check for overlaps between AHDB keys and heatmap nodes.

## OBSERVE
If no overlap is detected, support the alternative hypothesis that the systems are separate; otherwise inconclusive.

## LEARNING
- Status: supported
- Summary: AHDB deltas do not appear in context heatmap nodes, suggesting separate data shapes.
- Evidence: supervisor/db.py, supervisor/tests/test_context_heatmap.py
