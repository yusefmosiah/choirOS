# Experiment: q1-queue-throughput

**Date**: 2026-01-27T07:21:32.057219Z
**Question**: Do we need queues between input and supervisor processing?

## PREDICTION
A queued, multi-worker pipeline will show at least 3x throughput over direct single-thread processing under burst load.

## EXPERIMENT
Run a synthetic workload with sleep-based tasks, compare sequential throughput to a multi-worker queue using threads.

## OBSERVE
If throughput ratio exceeds 3x, mark hypothesis supported for synthetic load; otherwise inconclusive.

## LEARNING
- Status: supported
- Summary: Synthetic queue experiment shows parallel workers improve throughput, but it does not exercise NATS/JetStream.
- Evidence: synthetic:threaded-queue
