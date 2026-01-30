# Experiment: q1-queue-throughput

**Date**: 2026-01-29T01:32:01.232009Z
**Question**: Do we need queues between input and supervisor processing?

## PREDICTION
A queued, multi-worker pipeline will show at least 3x throughput over direct single-thread processing under burst load.

## EXPERIMENT
Use JetStream pull consumers on a dedicated research stream to compare single-worker throughput against a multi-worker consumer group.

## OBSERVE
If JetStream throughput ratio exceeds 3x, mark hypothesis supported; otherwise inconclusive.

## LEARNING
- Status: supported
- Summary: JetStream pull consumers show multi-worker throughput lift on queue workloads.
- Evidence: nats://, jetstream:pull_consumer
