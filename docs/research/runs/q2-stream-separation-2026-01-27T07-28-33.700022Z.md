# Experiment: q2-stream-separation

**Date**: 2026-01-27T07:28:33.700022Z
**Question**: Are we using NATS correctly by separating streams for inputs, observability, and modes?

## PREDICTION
Current event types cluster into inputs, observability, and mode events with high coverage, making stream separation feasible.

## EXPERIMENT
Create three JetStream streams with isolated subjects (inputs/observability/modes), publish one message to each, and verify stream isolation.

## OBSERVE
If each stream reports only its own message, mark separation supported; otherwise inconclusive.

## LEARNING
- Status: inconclusive
- Summary: JetStream stream separation experiment unavailable: NATS not reachable at localhost:4222 ([Errno 61] Connection refused)
- Evidence: nats://
