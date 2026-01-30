"""
PREDICTION: The research runner lists and executes registered experiments, writing
structured logs and per-run markdown summaries to the chosen output directory.
"""

import json
import tempfile
import unittest
from pathlib import Path

from supervisor.research.runner import list_experiments, run_experiments


class TestResearchRunner(unittest.TestCase):
    def test_list_experiments_includes_modes_classification(self) -> None:
        """
        PREDICTION: The experiment registry includes the modes-classification experiment.

        EXPERIMENT:
        1. Load experiment list from the registry.
        2. Collect experiment ids.

        OBSERVE:
        - The expected experiment id is present.
        - The list is non-empty.
        - Edge cases covered: empty registry would fail this test immediately.
        """
        experiments = list_experiments()
        ids = [spec.experiment_id for spec in experiments]

        self.assertTrue(ids)
        self.assertIn("q3-modes-classification", ids)

    def test_run_experiment_writes_logs(self) -> None:
        """
        PREDICTION: Running the research runner writes a JSONL log line and a markdown
        summary under the output root.

        EXPERIMENT:
        1. Run a single experiment with a temporary output root.
        2. Load the JSONL log and capture the markdown path.

        OBSERVE:
        - The JSONL log exists with a matching experiment id.
        - A markdown summary file exists in the runs directory.
        - Edge cases covered: output root does not exist before the run.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "research"
            runs = run_experiments(
                experiment_ids=["q3-modes-classification"],
                output_root=output_root,
                update_prompt=False,
            )

            self.assertEqual(len(runs), 1)
            log_path = output_root / "experiment_runs.jsonl"
            self.assertTrue(log_path.exists())

            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertTrue(lines)
            payload = json.loads(lines[-1])
            self.assertEqual(payload.get("experiment_id"), "q3-modes-classification")

            runs_dir = output_root / "runs"
            self.assertTrue(runs_dir.exists())
            markdown_files = list(runs_dir.glob("q3-modes-classification-*.md"))
            self.assertTrue(markdown_files)


if __name__ == "__main__":
    unittest.main()
