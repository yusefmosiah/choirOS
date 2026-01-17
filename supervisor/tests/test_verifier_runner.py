import tempfile
import unittest
from pathlib import Path
import sys

from supervisor.verifier_runner import ArtifactStore, VerifierRunner, VerifierSpec


class TestVerifierRunner(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.store = ArtifactStore(root=Path(self.tmp_dir.name))
        self.runner = VerifierRunner(store=self.store)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_runner_emits_artifacts_and_attestation(self) -> None:
        spec = VerifierSpec(
            verifier_id="V-TEST-PASS",
            command=[sys.executable, "-c", "print('ok')"],
        )
        result = self.runner.run(spec)

        self.assertEqual(result.status, "pass")
        self.assertTrue((Path(self.tmp_dir.name) / f"{result.artifact_hash}.log").exists())
        self.assertTrue((Path(self.tmp_dir.name) / f"{result.report_hash}.json").exists())
        self.assertTrue((Path(self.tmp_dir.name) / f"{result.attestation_hash}.json").exists())

    def test_runner_records_failure(self) -> None:
        spec = VerifierSpec(
            verifier_id="V-TEST-FAIL",
            command=[sys.executable, "-c", "import sys; print('bad'); sys.exit(2)"]
        )
        result = self.runner.run(spec)
        self.assertEqual(result.status, "fail")
        self.assertNotEqual(result.return_code, 0)


if __name__ == "__main__":
    unittest.main()
