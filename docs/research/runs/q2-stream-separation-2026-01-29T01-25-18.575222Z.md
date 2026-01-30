# Experiment: q2-stream-separation

**Date**: 2026-01-29T01:25:18.575222Z
**Question**: Are we using NATS correctly by separating streams for inputs, observability, and modes?

## PREDICTION
JetStream can isolate inputs, observability, and mode events into separate streams using subject filters.

## EXPERIMENT
Create three JetStream streams with isolated subjects (inputs/observability/modes), publish one message to each, and verify stream isolation.

## OBSERVE
If each stream reports only its own message, mark separation supported; otherwise inconclusive.

## LEARNING
- Status: inconclusive
- Summary: JetStream stream separation experiment unavailable: nats: BadRequestError: code=400 err_code=10065 description='subjects overlap with an existing stream'
- Evidence: nats://
