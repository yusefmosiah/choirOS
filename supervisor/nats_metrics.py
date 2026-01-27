from __future__ import annotations

import threading
from collections import deque
from typing import Deque


class NatsMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.deliveries_total = 0
        self.redeliveries_total = 0
        self.dedupe_hits = 0
        self.dedupe_misses = 0
        self.acks_total = 0
        self.nacks_total = 0
        self.dlq_total = 0
        self.handler_latencies_ms: Deque[float] = deque(maxlen=1000)
        self.ack_latencies_ms: Deque[float] = deque(maxlen=1000)

    def record_delivery(self, delivery_count: int) -> None:
        with self._lock:
            self.deliveries_total += 1
            if delivery_count > 1:
                self.redeliveries_total += 1

    def record_dedupe(self, hit: bool) -> None:
        with self._lock:
            if hit:
                self.dedupe_hits += 1
            else:
                self.dedupe_misses += 1

    def record_ack(self, latency_ms: float) -> None:
        with self._lock:
            self.acks_total += 1
            self.ack_latencies_ms.append(latency_ms)

    def record_nak(self) -> None:
        with self._lock:
            self.nacks_total += 1

    def record_dlq(self) -> None:
        with self._lock:
            self.dlq_total += 1

    def record_handler_latency(self, latency_ms: float) -> None:
        with self._lock:
            self.handler_latencies_ms.append(latency_ms)

    def snapshot(self) -> dict:
        with self._lock:
            deliveries = self.deliveries_total
            redeliveries = self.redeliveries_total
            dedupe_hits = self.dedupe_hits
            dedupe_misses = self.dedupe_misses
            acks = self.acks_total
            nacks = self.nacks_total
            dlq = self.dlq_total
            handler = list(self.handler_latencies_ms)
            ack = list(self.ack_latencies_ms)

        return {
            "deliveries_total": deliveries,
            "redeliveries_total": redeliveries,
            "redelivery_rate": (redeliveries / deliveries) if deliveries else 0.0,
            "dedupe_hits": dedupe_hits,
            "dedupe_misses": dedupe_misses,
            "dedupe_rate": (dedupe_hits / deliveries) if deliveries else 0.0,
            "acks_total": acks,
            "nacks_total": nacks,
            "dlq_total": dlq,
            "handler_latency_ms": _percentiles(handler),
            "ack_latency_ms": _percentiles(ack),
        }


def _percentiles(values: list[float]) -> dict:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    ordered = sorted(values)
    return {
        "p50": _percentile(ordered, 0.50),
        "p95": _percentile(ordered, 0.95),
        "p99": _percentile(ordered, 0.99),
    }


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    idx = int(round((len(values) - 1) * q))
    return float(values[max(0, min(idx, len(values) - 1))])


NATS_METRICS = NatsMetrics()
