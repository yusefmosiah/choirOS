"""Run orchestration: CALM -> VERIFY -> SKEPTICAL."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Callable, Iterable, Optional, Awaitable

from .db import EventStore
from .verifier_runner import VerifierRunner, VerifierSpec
from .verifier_plan import select_verifier_plan, build_verifier_specs


class RunOrchestrator:
    def __init__(self, store: EventStore, verifier_runner: Optional[VerifierRunner] = None) -> None:
        self.store = store
        self.verifier_runner = verifier_runner or VerifierRunner()

    def run(
        self,
        work_item_id: str,
        execute_run: Callable[[dict], bool],
        verifier_specs: Iterable[VerifierSpec],
        mood: str = "CALM",
    ) -> dict:
        run = self.store.create_run(work_item_id=work_item_id, mood=mood, status="running")
        run_id = run["id"]

        self.store.add_run_note(
            run_id,
            "note.status",
            {"status": "running", "mood": mood, "stage": "execute"},
        )

        try:
            success = bool(execute_run(run))
        except Exception as exc:
            success = False
            self.store.add_run_note(
                run_id,
                "note.hyperthesis",
                {"error": str(exc), "bound": "re-run with isolated executor"},
            )

        if not success:
            self.store.update_run(run_id, {"status": "failed", "mood": "SKEPTICAL"})
            self.store.add_run_note(
                run_id,
                "note.status",
                {"status": "failed", "mood": "SKEPTICAL", "stage": "verify"},
            )
            return {"run": self.store.get_run(run_id), "verifier_results": []}

        self.store.update_run(run_id, {"status": "verifying"})
        self.store.add_run_note(
            run_id,
            "note.status",
            {"status": "verifying", "mood": mood, "stage": "verify"},
        )

        results = []
        for spec in verifier_specs:
            result = self.verifier_runner.run(spec)
            results.append(result)
            self.store.add_run_verification(run_id, asdict(result))

        all_passed = all(result.status == "pass" for result in results)
        final_status = "verified" if all_passed else "failed"
        self.store.update_run(run_id, {"status": final_status, "mood": "SKEPTICAL"})
        self.store.add_run_note(
            run_id,
            "note.status",
            {"status": final_status, "mood": "SKEPTICAL", "stage": "adjudicate"},
        )

        if all_passed:
            self.store.add_commit_request(
                run_id,
                {
                    "verifier_results": [asdict(result) for result in results],
                    "status": "ready_for_review",
                },
            )

        return {"run": self.store.get_run(run_id), "verifier_results": results}

    async def run_async(
        self,
        work_item_id: str,
        execute_run: Callable[[dict], Awaitable[bool]],
        mood: str = "CALM",
        config_path: Optional[Path] = None,
    ) -> dict:
        run = self.store.create_run(work_item_id=work_item_id, mood=mood, status="running")
        run_id = run["id"]
        start_seq = self.store.get_latest_seq()

        self.store.add_run_note(
            run_id,
            "note.status",
            {"status": "running", "mood": mood, "stage": "execute"},
        )

        try:
            success = bool(await execute_run(run))
        except Exception as exc:
            success = False
            self.store.add_run_note(
                run_id,
                "note.hyperthesis",
                {"error": str(exc), "bound": "re-run with isolated executor"},
            )

        touched_paths = self.store.get_event_paths_since(start_seq)
        work_item = self.store.get_work_item(work_item_id) or {}
        required_verifiers = work_item.get("required_verifiers", [])
        risk_tier = work_item.get("risk_tier")

        plan = select_verifier_plan(
            touched_paths=touched_paths,
            mood=mood,
            required_verifiers=required_verifiers,
            risk_tier=risk_tier,
            config_path=config_path,
        )
        verifier_specs = build_verifier_specs(plan.verifier_ids, config_path=config_path)

        if not success:
            self.store.update_run(run_id, {"status": "failed", "mood": "SKEPTICAL"})
            self.store.add_run_note(
                run_id,
                "note.status",
                {"status": "failed", "mood": "SKEPTICAL", "stage": "verify"},
            )
            return {
                "run": self.store.get_run(run_id),
                "verifier_plan": plan.to_dict(),
                "verifier_results": [],
            }

        self.store.update_run(run_id, {"status": "verifying"})
        self.store.add_run_note(
            run_id,
            "note.status",
            {"status": "verifying", "mood": mood, "stage": "verify"},
        )

        results = []
        for spec in verifier_specs:
            result = self.verifier_runner.run(spec)
            results.append(result)
            self.store.add_run_verification(run_id, asdict(result))

        all_passed = all(result.status == "pass" for result in results)
        final_status = "verified" if all_passed else "failed"
        self.store.update_run(run_id, {"status": final_status, "mood": "SKEPTICAL"})
        self.store.add_run_note(
            run_id,
            "note.status",
            {"status": final_status, "mood": "SKEPTICAL", "stage": "adjudicate"},
        )

        if all_passed:
            self.store.add_commit_request(
                run_id,
                {
                    "verifier_plan": plan.to_dict(),
                    "verifier_results": [asdict(result) for result in results],
                    "status": "ready_for_review",
                },
            )

        return {
            "run": self.store.get_run(run_id),
            "verifier_plan": plan.to_dict(),
            "verifier_results": results,
        }
