import unittest
from pathlib import Path

from supervisor.verifier_plan import select_verifier_plan


class TestVerifierPlan(unittest.TestCase):
    def setUp(self) -> None:
        self.config_path = Path(__file__).resolve().parents[2] / "config" / "verifiers.yaml"

    def test_selects_scope_verifier(self) -> None:
        plan = select_verifier_plan(
            touched_paths=["supervisor/event_contract.py"],
            mood="CALM",
            config_path=self.config_path,
        )
        self.assertIn("V-01-EVENT-CONTRACT", plan.verifier_ids)
        self.assertIn("V-08-FAST-UNIT", plan.verifier_ids)

    def test_required_verifier_included(self) -> None:
        plan = select_verifier_plan(
            touched_paths=[],
            mood="CALM",
            required_verifiers=["V-03-RUN-STATE"],
            config_path=self.config_path,
        )
        self.assertIn("V-03-RUN-STATE", plan.verifier_ids)

    def test_unknown_required_recorded(self) -> None:
        plan = select_verifier_plan(
            touched_paths=[],
            mood="CALM",
            required_verifiers=["V-99-UNKNOWN"],
            config_path=self.config_path,
        )
        self.assertIn("V-99-UNKNOWN", plan.unknown_required)

    def test_skeptical_includes_fast_unit(self) -> None:
        plan = select_verifier_plan(
            touched_paths=["supervisor/db.py"],
            mood="SKEPTICAL",
            config_path=self.config_path,
        )
        self.assertIn("V-08-FAST-UNIT", plan.verifier_ids)
        self.assertIn("V-02-AHDB-PROJECTION", plan.verifier_ids)


if __name__ == "__main__":
    unittest.main()
