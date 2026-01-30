# Experiment: q3-modes-classification

**Date**: 2026-01-27T07:16:29.219671Z
**Question**: What are modes really - risk levels, verification strategies, or capability categories?

## PREDICTION
Mode definitions will cluster along capability boundaries (write/network/tool allowlists) more strongly than along explicit verification strategy fields.

## EXPERIMENT
Extract mode configurations from supervisor/mode_config.py and mode ids from supervisor/mode_engine.py, then compute capability groupings and budget deltas.

## OBSERVE
If capability groupings are clear and no verification strategy fields exist, support capability-categories hypothesis and mark others inconclusive.

## LEARNING
- Status: inconclusive
- Summary: Modes separate by capability (write/network) with no explicit verification strategy fields.
- Evidence: supervisor/mode_config.py, supervisor/mode_engine.py
