# Experiment: q2-stream-separation

**Date**: 2026-01-27T07:28:10.130731Z
**Question**: Are we using NATS correctly by separating streams for inputs, observability, and modes?

## PREDICTION
Current event types cluster into inputs, observability, and mode events with high coverage, making stream separation feasible.

## EXPERIMENT
Classify existing event types (from state.sqlite if present, else contract list) into stream categories and compute coverage.

## OBSERVE
If coverage across the three categories exceeds 90%, mark separation as supported; otherwise inconclusive.

## LEARNING
- Status: inconclusive
- Summary: JetStream stream separation experiment unavailable: NATS not reachable at localhost:4222 ([Errno 61] Connection refused)
- Evidence: nats://
