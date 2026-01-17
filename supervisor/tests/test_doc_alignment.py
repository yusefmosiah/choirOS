import unittest
from pathlib import Path


class TestDocAlignment(unittest.TestCase):
    def test_docs_index_entries_exist(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        index_path = repo_root / "docs" / "00_INDEX.md"
        lines = index_path.read_text(encoding="utf-8").splitlines()

        missing = []
        seen = set()

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("- "):
                continue
            entry = stripped[2:]
            if not entry:
                continue
            path = entry.split(" ")[0]
            if path in seen:
                continue
            seen.add(path)

            if not (
                path.startswith("docs/")
                or path.startswith("scripts/")
                or path.endswith(".md")
                or path.endswith(".sh")
            ):
                continue

            if not (repo_root / path).exists():
                missing.append(path)

        self.assertFalse(missing, f"Missing docs index entries: {missing}")


if __name__ == "__main__":
    unittest.main()
