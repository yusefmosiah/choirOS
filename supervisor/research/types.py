from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ExperimentContext:
    repo_root: Path
    output_root: Path
    run_id: str
    started_at: str


@dataclass(frozen=True)
class ExperimentObservation:
    status: str
    summary: str
    metrics: dict[str, Any]
    evidence: list[str]


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_id: str
    question: str
    prediction: str
    experiment: str
    observe: str
    runner: Callable[[ExperimentContext], ExperimentObservation]


@dataclass(frozen=True)
class ExperimentRun:
    run_id: str
    experiment_id: str
    question: str
    prediction: str
    experiment: str
    observe: str
    status: str
    started_at: str
    finished_at: str
    observation: ExperimentObservation
