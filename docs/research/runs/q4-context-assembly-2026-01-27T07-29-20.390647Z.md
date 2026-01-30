# Experiment: q4-context-assembly

**Date**: 2026-01-27T07:29:20.390647Z
**Question**: How should AHDB be assembled into worker context?

## PREDICTION
Ranking AHDB entries against task descriptions reduces context size while preserving relevant keys.

## EXPERIMENT
Score AHDB keys against sample tasks using token overlap and measure size reduction when selecting top-ranked keys.

## OBSERVE
If selected context is substantially smaller while retaining matches, mark ranking as promising but note lack of LLM performance validation.

## LEARNING
- Status: inconclusive
- Summary: Simple ranking reduces context size, but relevance and LLM performance remain untested.
- Evidence: state.sqlite
