"""
PREDICTION: Research experiment helpers produce stable classifications and ranking metrics
without requiring external services.
"""

import unittest

from supervisor.research.experiments import (
    _analyze_modes,
    _mode_influence_map,
    _mode_signal_category,
    _rank_context,
)
from supervisor.mode_engine import (
    MODE_BOLD,
    MODE_CALM,
    MODE_CONTRITE,
    MODE_CURIOUS,
    MODE_DEFERENTIAL,
    MODE_PARANOID,
    MODE_PETTY,
    MODE_SKEPTICAL,
)
from supervisor.research.types import ExperimentContext
from pathlib import Path
from datetime import datetime, timezone


class TestResearchExperiments(unittest.TestCase):
    def test_mode_classification_reports_hybrid(self) -> None:
        """
        PREDICTION: Mode analysis yields a hybrid classification when both capability
        boundaries and risk/verification signals are present.

        EXPERIMENT:
        1. Run the mode analysis experiment.
        2. Inspect classification and influence map.

        OBSERVE:
        - classification == "hybrid".
        - influence map contains at least one signal.
        - Edge cases covered: empty influence map would fail the test.
        """
        ctx = ExperimentContext(
            repo_root=Path("."),
            output_root=Path("."),
            run_id="test",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        observation = _analyze_modes(ctx)
        classification = observation.metrics["hypothesis_results"]["classification"]
        influences = observation.metrics["influential_flags"]

        self.assertEqual(classification, "hybrid")
        self.assertTrue(influences)

    def test_rank_context_hits_expected_keys(self) -> None:
        """
        PREDICTION: Ranking synthetic AHDB content hits expected keys with high hit-rate
        and yields a size reduction.

        EXPERIMENT:
        1. Build a synthetic AHDB state with task-aligned keys.
        2. Run ranking with top_k=1 and compute hit-rate/reduction.

        OBSERVE:
        - hit_rate == 1.0 for the provided tasks.
        - reduction_ratio > 0.
        - Edge cases covered: empty ahdb_state would drop hit_rate to 0.
        """
        tasks = [
            "decide if inputs need a work queue for throughput",
            "determine if NATS should separate streams",
        ]
        expected = {
            tasks[0]: "queue.throughput",
            tasks[1]: "nats.stream.separation",
        }
        ahdb_state = {
            "queue.throughput": {"claim": "queue improves throughput"},
            "nats.stream.separation": {"claim": "separate streams"},
            "extra": {"claim": "unrelated"},
        }
        ranking = _rank_context(ahdb_state, tasks, expected, top_k=1)

        self.assertEqual(ranking["hit_rate"], 1.0)
        self.assertGreater(ranking["reduction_ratio"], 0.0)

    def test_signal_category_mapping(self) -> None:
        """
        PREDICTION: Signal categorization maps known flag names into expected buckets.

        EXPERIMENT:
        1. Categorize a verification flag and a capability boundary flag.
        2. Compare to expected categories.

        OBSERVE:
        - "verifiers_regress" -> "verification".
        - "about_to_cross_privilege_boundary" -> "capability_boundary".
        - Edge cases covered: unrecognized flags default to "other".
        """
        self.assertEqual(_mode_signal_category("verifiers_regress"), "verification")
        self.assertEqual(
            _mode_signal_category("about_to_cross_privilege_boundary"),
            "capability_boundary",
        )
        self.assertEqual(_mode_signal_category("unknown_flag"), "other")

    def test_influence_map_has_known_modes(self) -> None:
        """
        PREDICTION: Influence map includes mode transitions when known signals are toggled.

        EXPERIMENT:
        1. Build an influence map for all mode ids.
        2. Verify the map includes at least one of the known modes.

        OBSERVE:
        - Influence map contains entries referencing MODE_SKEPTICAL or MODE_PARANOID.
        - Edge cases covered: no influences would fail this test.
        """
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
        influences = _mode_influence_map(mode_ids)
        flattened = {mode for modes in influences.values() for mode in modes}
        self.assertTrue(influences)
        self.assertTrue({MODE_SKEPTICAL, MODE_PARANOID}.intersection(flattened))


if __name__ == "__main__":
    unittest.main()
