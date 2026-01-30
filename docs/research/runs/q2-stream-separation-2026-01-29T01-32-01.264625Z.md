# Experiment: q2-stream-separation

**Date**: 2026-01-29T01:32:01.264625Z
**Question**: Are we using NATS correctly by separating streams for inputs, observability, and modes?

## PREDICTION
JetStream can isolate inputs, observability, and mode events into separate streams using subject filters.

## EXPERIMENT
Create three JetStream subjects (inputs/observability/modes), publish one message to each, and verify isolation via filtered consumers.

## OBSERVE
If each stream reports only its own message, mark separation supported; otherwise inconclusive.

## LEARNING
- Status: supported
- Summary: JetStream stream separation test confirms isolated subjects per stream.
- Evidence: nats://, jetstream:stream_info
