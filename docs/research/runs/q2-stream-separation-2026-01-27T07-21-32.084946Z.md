# Experiment: q2-stream-separation

**Date**: 2026-01-27T07:21:32.084946Z
**Question**: Are we using NATS correctly by separating streams for inputs, observability, and modes?

## PREDICTION
Current event types cluster into inputs, observability, and mode events with high coverage, making stream separation feasible.

## EXPERIMENT
Classify existing event types (from state.sqlite if present, else contract list) into stream categories and compute coverage.

## OBSERVE
If coverage across the three categories exceeds 90%, mark separation as supported; otherwise inconclusive.

## LEARNING
- Status: supported
- Summary: Event types can be grouped into inputs, observability, and mode events; this supports stream separation but is based on static classification.
- Evidence: supervisor/event_contract.py, state.sqlite
