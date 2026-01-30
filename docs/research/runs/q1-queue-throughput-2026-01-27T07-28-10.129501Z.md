# Experiment: q1-queue-throughput

**Date**: 2026-01-27T07:28:10.129501Z
**Question**: Do we need queues between input and supervisor processing?

## PREDICTION
A queued, multi-worker pipeline will show at least 3x throughput over direct single-thread processing under burst load.

## EXPERIMENT
Run a synthetic workload with sleep-based tasks, compare sequential throughput to a multi-worker queue using threads.

## OBSERVE
If throughput ratio exceeds 3x, mark hypothesis supported for synthetic load; otherwise inconclusive.

## LEARNING
- Status: inconclusive
- Summary: JetStream queue experiment unavailable: NATS not reachable at localhost:4222 ([Errno 61] Connection refused)
- Evidence: nats://
