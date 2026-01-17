import unittest
from pathlib import Path

from supervisor.event_contract import (
    CHOIR_EVENT_TYPES_V0,
    build_subject,
    normalize_event_type,
)


class TestEventContract(unittest.TestCase):
    def test_build_subject(self) -> None:
        self.assertEqual(
            build_subject("local", "agent", "file.write"),
            "choiros.local.agent.file.write",
        )

    def test_normalize_note_types(self) -> None:
        self.assertEqual(
            normalize_event_type("NOTE/REQUEST_VERIFY"),
            "note.request.verify",
        )
        self.assertEqual(
            normalize_event_type("NOTE_STATUS"),
            "note.status",
        )
        self.assertEqual(
            normalize_event_type("note.conjecture"),
            "note.conjecture",
        )

    def test_normalize_receipt_types(self) -> None:
        self.assertEqual(
            normalize_event_type("READ_RECEIPT"),
            "receipt.read",
        )
        self.assertEqual(
            normalize_event_type("TIMEOUT_RECEIPT"),
            "receipt.timeout",
        )
        self.assertEqual(
            normalize_event_type("RECEIPT/CONTEXT_FOOTPRINT"),
            "receipt.context.footprint",
        )

    def test_event_types_match_spec(self) -> None:
        doc_path = Path(__file__).resolve().parents[2] / "docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md"
        text = doc_path.read_text(encoding="utf-8")
        lines = text.splitlines()

        start_idx = None
        for idx, line in enumerate(lines):
            if line.strip() == "## Canonical event types (v0)":
                start_idx = idx
                break

        self.assertIsNotNone(start_idx, "Missing canonical event types section in spec")

        types_in_doc: list[str] = []
        for line in lines[start_idx + 1 :]:
            if line.startswith("## "):
                break
            stripped = line.strip()
            if stripped.startswith("- "):
                types_in_doc.append(stripped[2:].strip())

        self.assertTrue(types_in_doc, "No canonical event types found in spec")
        self.assertEqual(set(types_in_doc), set(CHOIR_EVENT_TYPES_V0))


if __name__ == "__main__":
    unittest.main()
