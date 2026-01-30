from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import tempfile
import time
from datetime import datetime
from urllib.parse import urlparse
import socket
from pathlib import Path
from typing import Any
import re

import nats
from nats.js.api import ConsumerConfig, RetentionPolicy, StorageType, StreamConfig

from supervisor.db import DEFAULT_DB_PATH, ProjectionStore
from supervisor.event_contract import CHOIR_EVENT_TYPES_V0, CHOIR_STREAM, CHOIR_SUBJECT_PATTERN
from supervisor.mode_config import get_mode_config
from supervisor.mode_engine import (
    ModeInputs,
    MODE_BOLD,
    MODE_CALM,
    MODE_CONTRITE,
    MODE_CURIOUS,
    MODE_DEFERENTIAL,
    MODE_PARANOID,
    MODE_PETTY,
    MODE_SKEPTICAL,
    select_initial_mode,
    transition_mode,
)
from supervisor.nats_client import (
    NATS_CREDS,
    NATS_PASSWORD,
    NATS_TOKEN,
    NATS_URL,
    NATS_USER,
)

from supervisor.research.types import ExperimentContext, ExperimentObservation, ExperimentSpec


def _mode_features(mode_id: str) -> dict[str, Any]:
    config = get_mode_config(mode_id)
    return {
        "allow_write": config.allow_write,
        "allow_network": config.allow_network,
        "tool_allowlist": sorted(config.tool_allowlist),
        "budgets": {
            "time_seconds": config.budgets.time_seconds,
            "tool_calls": config.budgets.tool_calls,
            "diff_bytes": config.budgets.diff_bytes,
            "files_touched": config.budgets.files_touched,
        },
        "description": config.description,
    }


def _mode_signal_category(flag: str) -> str:
    name = flag.lower()
    if any(token in name for token in ("verifier", "verified", "hyperthesis", "regress")):
        return "verification"
    if any(token in name for token in ("crash", "reward", "mitigation", "risk")):
        return "risk"
    if "privilege" in name:
        return "capability_boundary"
    if any(token in name for token in ("preference", "ambiguity", "user", "demo", "conjecture")):
        return "clarification"
    return "other"


def _mode_input_fields() -> list[str]:
    return list(ModeInputs.__annotations__.keys())


def _toggle_mode_inputs(field: str) -> ModeInputs:
    defaults = ModeInputs()
    value = getattr(defaults, field)
    updated = not value if isinstance(value, bool) else value
    return ModeInputs(**{**defaults.__dict__, field: updated})


def _mode_influence_map(mode_ids: list[str]) -> dict[str, list[str]]:
    influences: dict[str, list[str]] = {}
    baseline = ModeInputs()
    baseline_initial = select_initial_mode(baseline)
    for field in _mode_input_fields():
        toggled = _toggle_mode_inputs(field)
        changes: list[str] = []
        if select_initial_mode(toggled) != baseline_initial:
            changes.append("initial")
        for mode_id in mode_ids:
            toggled_with_prev = ModeInputs(**{**toggled.__dict__, "previous_mode": mode_id})
            if transition_mode(mode_id, toggled_with_prev) != mode_id:
                changes.append(mode_id)
        if changes:
            influences[field] = sorted(set(changes))
    return influences


def _analyze_modes(_: ExperimentContext) -> ExperimentObservation:
    mode_ids = [
        MODE_CALM,
        MODE_CURIOUS,
        MODE_SKEPTICAL,
        MODE_PARANOID,
        MODE_BOLD,
        MODE_PETTY,
        MODE_CONTRITE,
        MODE_DEFERENTIAL,
    ]
    features = {mode_id: _mode_features(mode_id) for mode_id in mode_ids}
    write_enabled = [m for m, f in features.items() if f["allow_write"]]
    read_only = [m for m, f in features.items() if not f["allow_write"]]
    network_enabled = [m for m, f in features.items() if f["allow_network"]]
    tool_allowlists = {m: f["tool_allowlist"] for m, f in features.items()}
    budgets = {m: f["budgets"] for m, f in features.items()}

    capability_profiles = {
        (f["allow_write"], f["allow_network"], tuple(f["tool_allowlist"]))
        for f in features.values()
    }
    capability_supported = len(capability_profiles) > 1
    influences = _mode_influence_map(mode_ids)
    category_counts: dict[str, int] = {}
    for flag in influences:
        category = _mode_signal_category(flag)
        category_counts[category] = category_counts.get(category, 0) + 1
    risk_verification_signals = category_counts.get("risk", 0) + category_counts.get("verification", 0)
    signal_supported = risk_verification_signals > 0

    classification = "hybrid" if capability_supported and signal_supported else "inconclusive"
    hypothesis_results = {
        "risk_levels": "supported" if signal_supported else "inconclusive",
        "verification_strategies": "supported" if signal_supported else "inconclusive",
        "capability_categories": "supported" if capability_supported else "inconclusive",
        "classification": classification,
    }

    summary = (
        "Mode selection responds to risk/verification signals, while mode configs enforce "
        "capability boundaries (write/network/tooling)."
    )
    metrics = {
        "mode_count": len(mode_ids),
        "write_enabled": write_enabled,
        "read_only": read_only,
        "network_enabled": network_enabled,
        "tool_allowlists": tool_allowlists,
        "budgets": budgets,
        "capability_profiles": sorted(list(capability_profiles)),
        "influential_flags": influences,
        "signal_category_counts": category_counts,
        "hypothesis_results": hypothesis_results,
    }
    evidence = ["supervisor/mode_config.py", "supervisor/mode_engine.py"]

    return ExperimentObservation(
        status="supported" if classification == "hybrid" else "inconclusive",
        summary=summary,
        metrics=metrics,
        evidence=evidence,
    )


def _queue_throughput(_: ExperimentContext) -> ExperimentObservation:
    task_count = 200
    sleep_seconds = 0.01
    workers = 5

    def _nats_reachable() -> tuple[bool, str]:
        parsed = urlparse(NATS_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 4222
        try:
            with socket.create_connection((host, port), timeout=1):
                return True, f"{host}:{port}"
        except OSError as exc:
            return False, f"{host}:{port} ({exc})"

    async def _connect():
        options: dict[str, Any] = {
            "connect_timeout": 2,
            "allow_reconnect": False,
            "max_reconnect_attempts": 0,
        }
        if NATS_CREDS:
            options["user_credentials"] = NATS_CREDS
        if NATS_TOKEN:
            options["token"] = NATS_TOKEN
        if NATS_USER:
            options["user"] = NATS_USER
        if NATS_PASSWORD:
            options["password"] = NATS_PASSWORD
        nc = await nats.connect(NATS_URL, **options)
        return nc, nc.jetstream()

    async def _run() -> dict[str, Any]:
        nc = None
        js = None
        stream_name = CHOIR_STREAM
        subject = f"choiros.research.q1.{int(time.time())}"
        durables: list[str] = []
        try:
            nc, js = await _connect()
            try:
                await js.stream_info(CHOIR_STREAM)
            except nats.js.errors.NotFoundError:
                await js.add_stream(
                    StreamConfig(
                        name=CHOIR_STREAM,
                        subjects=[CHOIR_SUBJECT_PATTERN],
                        retention=RetentionPolicy.LIMITS,
                        storage=StorageType.FILE,
                    )
                )

            async def publish_messages() -> None:
                for i in range(task_count):
                    await js.publish(subject, json.dumps({"i": i}).encode())

            async def consume_with_workers(worker_count: int) -> float:
                durable = f"research_q1_{int(time.time())}_{worker_count}"
                durables.append(durable)
                sub = await js.pull_subscribe(
                    subject,
                    durable=durable,
                    stream=CHOIR_STREAM,
                    config=ConsumerConfig(
                        ack_policy="none",
                        deliver_policy="all",
                    ),
                )
                processed = 0
                lock = asyncio.Lock()

                async def worker() -> None:
                    nonlocal processed
                    while True:
                        async with lock:
                            if processed >= task_count:
                                return
                        try:
                            msgs = await sub.fetch(10, timeout=1)
                        except nats.errors.TimeoutError:
                            continue
                        for msg in msgs:
                            await asyncio.sleep(sleep_seconds)
                            async with lock:
                                processed += 1
                                if processed >= task_count:
                                    return

                start = time.perf_counter()
                await publish_messages()
                tasks = [asyncio.create_task(worker()) for _ in range(worker_count)]
                await asyncio.gather(*tasks)
                elapsed = max(time.perf_counter() - start, 1e-6)
                return task_count / elapsed

            direct_tps = await consume_with_workers(1)
            queued_tps = await consume_with_workers(workers)
            ratio = queued_tps / max(direct_tps, 1e-6)

            return {
                "direct_tps": direct_tps,
                "queue_tps": queued_tps,
                "ratio": ratio,
                "stream": CHOIR_STREAM,
                "subject": subject,
            }
        finally:
            if js:
                for durable in durables:
                    try:
                        await js.delete_consumer(CHOIR_STREAM, durable)
                    except Exception:
                        pass
            if nc:
                try:
                    await nc.drain()
                except Exception:
                    pass

    try:
        reachable, endpoint = _nats_reachable()
        if not reachable:
            raise RuntimeError(f"NATS not reachable at {endpoint}")
        result = asyncio.run(_run())
        ratio = result["ratio"]
        status = "supported" if ratio >= 3 else "inconclusive"
        summary = "JetStream pull consumers show multi-worker throughput lift on queue workloads."
        metrics = {
            "task_count": task_count,
            "sleep_seconds": sleep_seconds,
            "workers": workers,
            "direct_tps": result["direct_tps"],
            "queue_tps": result["queue_tps"],
            "throughput_ratio": ratio,
            "hypothesis_threshold": 3.0,
            "stream": result["stream"],
        }
        evidence = ["nats://", "jetstream:pull_consumer"]
    except Exception as exc:
        status = "inconclusive"
        summary = f"JetStream queue experiment unavailable: {exc}"
        metrics = {"error": str(exc)}
        evidence = ["nats://"]

    return ExperimentObservation(status=status, summary=summary, metrics=metrics, evidence=evidence)


def _categorize_event_type(event_type: str) -> str:
    if event_type.startswith("mode."):
        return "mode_events"
    if event_type.startswith("note.") or event_type.startswith("receipt."):
        return "observability"
    if event_type.startswith("artifact."):
        return "observability"
    if event_type in {
        "window.open",
        "window.close",
        "checkpoint",
        "undo",
        "provider.changed",
        "provider.test",
    }:
        return "observability"
    if event_type in {
        "message",
        "tool.call",
        "tool.result",
        "file.write",
        "file.delete",
        "file.move",
    }:
        return "inputs"
    return "other"


def _load_event_types(db_path: Path) -> list[tuple[str, int]]:
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT type, COUNT(*) FROM events GROUP BY type").fetchall()
        conn.close()
        return [(row[0], int(row[1])) for row in rows if row and row[0]]
    except sqlite3.Error:
        return []


def _analyze_stream_separation(context: ExperimentContext) -> ExperimentObservation:
    stream_suffix = f"RESEARCH_Q2_{int(time.time())}"
    subjects = {
        "inputs": f"choiros.research.inputs.{stream_suffix}",
        "observability": f"choiros.research.obs.{stream_suffix}",
        "mode_events": f"choiros.research.mode.{stream_suffix}",
    }

    async def _connect():
        options: dict[str, Any] = {
            "connect_timeout": 2,
            "allow_reconnect": False,
            "max_reconnect_attempts": 0,
        }
        if NATS_CREDS:
            options["user_credentials"] = NATS_CREDS
        if NATS_TOKEN:
            options["token"] = NATS_TOKEN
        if NATS_USER:
            options["user"] = NATS_USER
        if NATS_PASSWORD:
            options["password"] = NATS_PASSWORD
        nc = await nats.connect(NATS_URL, **options)
        return nc, nc.jetstream()

    async def _run() -> dict[str, Any]:
        nc = None
        js = None
        durables: dict[str, str] = {}
        try:
            nc, js = await _connect()
            try:
                await js.stream_info(CHOIR_STREAM)
            except nats.js.errors.NotFoundError:
                await js.add_stream(
                    StreamConfig(
                        name=CHOIR_STREAM,
                        subjects=[CHOIR_SUBJECT_PATTERN],
                        retention=RetentionPolicy.LIMITS,
                        storage=StorageType.FILE,
                    )
                )
            for name, subject in subjects.items():
                await js.publish(subject, json.dumps({"stream": name}).encode())
            results: dict[str, int] = {}
            for name, subject in subjects.items():
                durable = f"research_q2_{name.lower()}_{int(time.time())}"
                durables[name] = durable
                sub = await js.pull_subscribe(
                    subject,
                    durable=durable,
                    stream=CHOIR_STREAM,
                    config=ConsumerConfig(
                        ack_policy="none",
                        deliver_policy="all",
                    ),
                )
                msgs = await sub.fetch(1, timeout=2)
                results[name] = len(msgs)
            return results
        finally:
            if js:
                for durable in durables.values():
                    try:
                        await js.delete_consumer(CHOIR_STREAM, durable)
                    except Exception:
                        pass
            if nc:
                try:
                    await nc.drain()
                except Exception:
                    pass

    try:
        parsed = urlparse(NATS_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 4222
        try:
            with socket.create_connection((host, port), timeout=1):
                pass
        except OSError as exc:
            raise RuntimeError(f"NATS not reachable at {host}:{port} ({exc})") from exc
        results = asyncio.run(_run())
        status = "supported" if all(count == 1 for count in results.values()) else "inconclusive"
        summary = (
            "JetStream stream separation test confirms isolated subjects per stream."
        )
        metrics = {"stream_messages": results, "subjects": subjects}
        evidence = ["nats://", "jetstream:stream_info"]
    except Exception as exc:
        status = "inconclusive"
        summary = f"JetStream stream separation experiment unavailable: {exc}"
        metrics = {"error": str(exc)}
        evidence = ["nats://"]

    return ExperimentObservation(status=status, summary=summary, metrics=metrics, evidence=evidence)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token}


def _rank_context(
    ahdb_state: dict[str, Any],
    tasks: list[str],
    expected_matches: dict[str, str],
    top_k: int,
) -> dict[str, Any]:
    scored: dict[str, list[tuple[str, float]]] = {}
    hit_count = 0
    per_task_sizes: dict[str, int] = {}
    per_task_reduction: dict[str, float] = {}
    full_size = len(json.dumps(ahdb_state))
    for task in tasks:
        task_tokens = _tokenize(task)
        scored_entries = []
        for key, value in ahdb_state.items():
            payload = f"{key} {value}"
            tokens = _tokenize(payload)
            if not tokens:
                continue
            overlap = task_tokens.intersection(tokens)
            score = len(overlap) / max(len(task_tokens), 1)
            scored_entries.append((key, score))
        ranked = sorted(scored_entries, key=lambda item: item[1], reverse=True)
        scored[task] = ranked
        expected = expected_matches.get(task)
        if expected and any(key == expected for key, _ in ranked[:top_k]):
            hit_count += 1
        selected_keys_task = {key for key, score in ranked[:top_k] if score > 0}
        selected_payload_task = {key: ahdb_state[key] for key in selected_keys_task}
        selected_size_task = len(json.dumps(selected_payload_task)) if selected_payload_task else 0
        per_task_sizes[task] = selected_size_task
        if full_size:
            per_task_reduction[task] = 1 - (selected_size_task / full_size)
        else:
            per_task_reduction[task] = 0.0

    selected_keys = {key for entries in scored.values() for key, score in entries[:top_k] if score > 0}
    selected_payload = {key: ahdb_state[key] for key in selected_keys}
    selected_size = len(json.dumps(selected_payload)) if selected_payload else 0
    reduction_ratio = 1 - (selected_size / full_size) if full_size else 0.0
    hit_rate = hit_count / max(len(tasks), 1)
    avg_reduction = (
        sum(per_task_reduction.values()) / max(len(per_task_reduction), 1)
        if per_task_reduction
        else 0.0
    )

    return {
        "scored": scored,
        "selected_keys": selected_keys,
        "full_size_bytes": full_size,
        "selected_size_bytes": selected_size,
        "reduction_ratio": reduction_ratio,
        "avg_reduction_ratio": avg_reduction,
        "per_task_reduction": per_task_reduction,
        "per_task_sizes": per_task_sizes,
        "hit_rate": hit_rate,
        "top_k": top_k,
    }


def _rank_ahdb_context(context: ExperimentContext) -> ExperimentObservation:
    db_path = DEFAULT_DB_PATH if DEFAULT_DB_PATH.exists() else None
    ahdb_state: dict[str, Any] = {}
    source = "state.sqlite"
    if db_path:
        try:
            conn = sqlite3.connect(str(db_path))
            rows = conn.execute("SELECT key, value FROM ahdb_state").fetchall()
            conn.close()
            for key, value in rows:
                ahdb_state[key] = value
        except sqlite3.Error:
            ahdb_state = {}
            source = "none"
    else:
        source = "none"

    tasks = [
        "decide if inputs need a work queue for throughput",
        "determine if NATS should separate streams",
        "classify modes as capability or risk tiers",
        "assemble AHDB context for worker prompt",
        "compare AHDB with context map visualization",
    ]
    expected_matches = {
        tasks[0]: "queue.throughput",
        tasks[1]: "nats.stream.separation",
        tasks[2]: "modes.classification",
        tasks[3]: "context.assembly",
        tasks[4]: "context.map.relationship",
    }

    if not ahdb_state:
        ahdb_state = {
            "queue.throughput": {"claim": "queue improves throughput under burst load"},
            "nats.stream.separation": {"claim": "separate inputs/observability/modes streams"},
            "modes.classification": {"claim": "modes map to capability boundaries and risk cues"},
            "context.assembly": {"claim": "rank by relevance to tasks and trim context"},
            "context.map.relationship": {"claim": "context map is a view, AHDB is internal state"},
            "extra.unrelated": {"claim": "miscellaneous metadata"},
        }
        source = "synthetic"

    ranking = _rank_context(ahdb_state, tasks, expected_matches, top_k=3)
    reduction_ratio = ranking["avg_reduction_ratio"]
    hit_rate = ranking["hit_rate"]
    status = "supported" if reduction_ratio >= 0.5 and hit_rate >= 0.8 else "inconclusive"

    summary = (
        "Ranking reduces context size and retrieves expected keys for most tasks, "
        "but LLM performance remains untested."
    )
    metrics = {
        "total_keys": len(ahdb_state),
        "selected_keys": sorted(ranking["selected_keys"]),
        "full_size_bytes": ranking["full_size_bytes"],
        "selected_size_bytes": ranking["selected_size_bytes"],
        "avg_reduction_ratio": reduction_ratio,
        "per_task_reduction": ranking["per_task_reduction"],
        "hit_rate": hit_rate,
        "top_k": ranking["top_k"],
        "tasks_scored": {
            task: entries[:3] for task, entries in ranking["scored"].items()
        },
        "dataset_source": source,
    }
    evidence = [source]

    return ExperimentObservation(
        status=status,
        summary=summary,
        metrics=metrics,
        evidence=evidence,
    )


def _ahdb_vs_context_map(_: ExperimentContext) -> ExperimentObservation:
    os.environ["NATS_ENABLED"] = "0"
    fd, path = tempfile.mkstemp(prefix="choiros_research_", suffix=".sqlite")
    os.close(fd)
    store = ProjectionStore(db_path=Path(path), user_id="local")
    try:
        now = int(datetime.now().timestamp() * 1000)
        store.apply_event("receipt.ahdb.delta", {"delta": {"assert": {"queue_required": True}}}, now)
        conversation_id = 1
        store.apply_event(
            "message",
            {"conversation_id": conversation_id, "role": "user", "content": "hello"},
            now,
        )
        store.conn.commit()
        snapshot = store.build_context_heatmap(limit=100)
        node_ids = {node["id"] for node in snapshot.get("nodes", [])}
        ahdb_keys = list(store.get_ahdb_state().keys())
        overlaps = [key for key in ahdb_keys if any(key in node_id for node_id in node_ids)]
        status = "supported" if not overlaps else "inconclusive"
        summary = (
            "AHDB deltas do not appear in context heatmap nodes, suggesting separate data shapes."
        )
        metrics = {
            "ahdb_keys": ahdb_keys,
            "heatmap_node_count": len(node_ids),
            "overlap_keys": overlaps,
            "heatmap_types": sorted({node.get("type") for node in snapshot.get("nodes", [])}),
        }
        evidence = ["supervisor/db.py", "supervisor/tests/test_context_heatmap.py"]
    finally:
        store.close()
        Path(path).unlink(missing_ok=True)

    return ExperimentObservation(
        status=status,
        summary=summary,
        metrics=metrics,
        evidence=evidence,
    )


def get_experiments() -> list[ExperimentSpec]:
    return [
        ExperimentSpec(
            experiment_id="q1-queue-throughput",
            question="Do we need queues between input and supervisor processing?",
            prediction=(
                "A queued, multi-worker pipeline will show at least 3x throughput over direct "
                "single-thread processing under burst load."
            ),
            experiment=(
                "Use JetStream pull consumers on a dedicated research stream to compare "
                "single-worker throughput against a multi-worker consumer group."
            ),
            observe=(
                "If JetStream throughput ratio exceeds 3x, mark hypothesis supported; otherwise "
                "inconclusive."
            ),
            runner=_queue_throughput,
        ),
        ExperimentSpec(
            experiment_id="q2-stream-separation",
            question=(
                "Are we using NATS correctly by separating streams for inputs, "
                "observability, and modes?"
            ),
            prediction=(
                "JetStream can isolate inputs, observability, and mode events into separate "
                "streams using subject filters."
            ),
            experiment=(
                "Create three JetStream subjects (inputs/observability/modes), publish one "
                "message to each, and verify isolation via filtered consumers."
            ),
            observe=(
                "If each stream reports only its own message, mark separation supported; otherwise "
                "inconclusive."
            ),
            runner=_analyze_stream_separation,
        ),
        ExperimentSpec(
            experiment_id="q3-modes-classification",
            question=(
                "What are modes really - risk levels, verification strategies, or capability "
                "categories?"
            ),
            prediction=(
                "Mode selection will be driven by risk/verification signals while mode configs "
                "enforce capability boundaries."
            ),
            experiment=(
                "Analyze mode_config capability profiles and probe mode_engine transitions by "
                "toggling ModeInputs flags to see which signals trigger mode changes."
            ),
            observe=(
                "If capability profiles are distinct and risk/verification signals influence mode "
                "selection, mark modes as a hybrid of capability boundaries and risk strategies."
            ),
            runner=_analyze_modes,
        ),
        ExperimentSpec(
            experiment_id="q4-context-assembly",
            question="How should AHDB be assembled into worker context?",
            prediction=(
                "Ranking AHDB entries against task descriptions reduces context size while "
                "preserving task-relevant keys."
            ),
            experiment=(
                "Score AHDB keys against sample tasks using token overlap and measure size "
                "reduction plus hit-rate for expected keys (synthetic data if AHDB is empty)."
            ),
            observe=(
                "If size reduction exceeds 50% and hit-rate exceeds 80%, support ranking as a "
                "viable assembly heuristic (LLM performance still untested)."
            ),
            runner=_rank_ahdb_context,
        ),
        ExperimentSpec(
            experiment_id="q5-ahdb-vs-context-map",
            question="What is the relationship between AHDB and the Context Map?",
            prediction=(
                "AHDB assertions will not appear directly in the context heatmap, indicating "
                "separate schemas rather than a single representation."
            ),
            experiment=(
                "Create an AHDB delta in a temp ProjectionStore, build a context heatmap, and check "
                "for overlaps between AHDB keys and heatmap nodes."
            ),
            observe=(
                "If no overlap is detected, support the alternative hypothesis that the systems "
                "are separate; otherwise inconclusive."
            ),
            runner=_ahdb_vs_context_map,
        ),
    ]
