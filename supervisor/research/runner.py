from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from supervisor.research.experiments import get_experiments
from supervisor.research.types import (
    ExperimentContext,
    ExperimentObservation,
    ExperimentRun,
    ExperimentSpec,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_output_root(path: Optional[Path]) -> Path:
    root = path or (_project_root() / "docs" / "research")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_jsonl(path: Path, payload: dict) -> None:
    line = json.dumps(payload, sort_keys=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _write_markdown(path: Path, run: ExperimentRun) -> None:
    observation = run.observation
    content = [
        f"# Experiment: {run.experiment_id}",
        "",
        f"**Date**: {run.finished_at}",
        f"**Question**: {run.question}",
        "",
        "## PREDICTION",
        run.prediction,
        "",
        "## EXPERIMENT",
        run.experiment,
        "",
        "## OBSERVE",
        run.observe,
        "",
        "## LEARNING",
        f"- Status: {run.status}",
        f"- Summary: {observation.summary}",
        f"- Evidence: {', '.join(observation.evidence) if observation.evidence else 'none'}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _load_runs(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    runs = []
    for line in lines:
        if not line.strip():
            continue
        try:
            runs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return runs


def _update_completed_experiments(prompt_path: Path, log_path: Path) -> None:
    text = prompt_path.read_text(encoding="utf-8")
    runs = _load_runs(log_path)
    latest: dict[str, dict] = {}
    for entry in runs:
        experiment_id = entry.get("experiment_id")
        finished_at = entry.get("finished_at")
        if not experiment_id or not finished_at:
            continue
        existing = latest.get(experiment_id)
        if not existing or finished_at > existing.get("finished_at", ""):
            latest[experiment_id] = entry
    ordered = sorted(latest.values(), key=lambda item: item.get("finished_at", ""))
    if not ordered:
        bullets = "*None yet - this is the starting point*"
    else:
        lines = []
        for item in ordered:
            exp_id = item.get("experiment_id", "unknown")
            status = item.get("status", "unknown")
            finished = item.get("finished_at", "unknown")
            summary = item.get("observation", {}).get("summary", "")
            lines.append(f"- {finished} | {exp_id} | {status} | {summary}")
        bullets = "\n".join(lines)

    marker = "### Completed Experiments"
    if marker not in text:
        return
    parts = text.split(marker)
    before = parts[0]
    after = marker.join(parts[1:])
    section_start = "\n\n"
    section_end = "\n\n---\n"
    if section_end not in after:
        return
    suffix = after.split(section_end, maxsplit=1)[1]
    updated = before + marker + section_start + bullets + section_end + suffix
    prompt_path.write_text(updated, encoding="utf-8")


def _to_run(
    spec: ExperimentSpec,
    observation: ExperimentObservation,
    run_id: str,
    started_at: str,
) -> ExperimentRun:
    finished_at = _timestamp()
    return ExperimentRun(
        run_id=run_id,
        experiment_id=spec.experiment_id,
        question=spec.question,
        prediction=spec.prediction,
        experiment=spec.experiment,
        observe=spec.observe,
        status=observation.status,
        started_at=started_at,
        finished_at=finished_at,
        observation=observation,
    )


def run_experiments(
    experiment_ids: Optional[Iterable[str]] = None,
    output_root: Optional[Path] = None,
    update_prompt: bool = True,
    prompt_path: Optional[Path] = None,
) -> list[ExperimentRun]:
    output_root = _ensure_output_root(output_root)
    log_path = output_root / "experiment_runs.jsonl"
    experiments = get_experiments()
    by_id = {spec.experiment_id: spec for spec in experiments}
    if experiment_ids:
        selected = [by_id[exp_id] for exp_id in experiment_ids if exp_id in by_id]
    else:
        selected = experiments

    runs: list[ExperimentRun] = []
    for spec in selected:
        run_id = str(uuid.uuid4())
        started_at = _timestamp()
        context = ExperimentContext(
            repo_root=_project_root(),
            output_root=output_root,
            run_id=run_id,
            started_at=started_at,
        )
        try:
            observation = spec.runner(context)
        except Exception as exc:
            observation = ExperimentObservation(
                status="failed",
                summary=str(exc),
                metrics={"error": str(exc)},
                evidence=[],
            )
        run = _to_run(spec, observation, run_id, started_at)
        runs.append(run)
        _write_jsonl(log_path, _serialize_run(run))
        safe_ts = run.finished_at.replace(":", "-")
        md_path = output_root / "runs" / f"{run.experiment_id}-{safe_ts}.md"
        _write_markdown(md_path, run)

    if update_prompt:
        prompt_path = prompt_path or (_project_root() / "AHDB_RESEARCH_PROMPT.md")
        if prompt_path.exists():
            _update_completed_experiments(prompt_path, log_path)

    return runs


def _serialize_run(run: ExperimentRun) -> dict:
    payload = asdict(run)
    payload["observation"] = asdict(run.observation)
    return payload


def list_experiments() -> list[ExperimentSpec]:
    return get_experiments()


def _print_experiments(experiments: list[ExperimentSpec]) -> None:
    for spec in experiments:
        print(f"{spec.experiment_id}: {spec.question}")


def _serialize_spec(spec: ExperimentSpec) -> dict:
    return {
        "experiment_id": spec.experiment_id,
        "question": spec.question,
        "prediction": spec.prediction,
        "experiment": spec.experiment,
        "observe": spec.observe,
        "runner": getattr(spec.runner, "__name__", "runner"),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="research-runner")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--json", action="store_true")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--id", dest="ids", action="append")
    run_parser.add_argument("--output-root")
    run_parser.add_argument("--no-update-prompt", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "list":
        experiments = list_experiments()
        if args.json:
            print(json.dumps([_serialize_spec(spec) for spec in experiments], indent=2))
        else:
            _print_experiments(experiments)
        return 0

    if args.command == "run":
        output_root = Path(args.output_root) if args.output_root else None
        run_experiments(
            experiment_ids=args.ids,
            output_root=output_root,
            update_prompt=not args.no_update_prompt,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
