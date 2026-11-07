"""Journey: specs/journeys/JOURNEY-release-publication.md."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def load_module(self):
        spec = importlib.util.spec_from_file_location("release_metadata", ROOT / "scripts/release-metadata.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_incomplete_release_is_rejected(self):
        module = self.load_module()
        with tempfile.TemporaryDirectory() as work:
            with self.assertRaisesRegex(ValueError, "missing release artifacts"):
                module.prepare(Path(work), "0.1.0", "a" * 40)

    def test_complete_release_checksums_cover_exact_bytes_and_source(self):
        module = self.load_module()
        with tempfile.TemporaryDirectory() as work:
            directory = Path(work)
            for name in module.required_artifacts("0.1.0"):
                (directory / name).write_bytes(name.encode())
            module.prepare(directory, "0.1.0", "a" * 40)
            manifest = json.loads((directory / "release.json").read_text())
            self.assertEqual(manifest["source_revision"], "a" * 40)
            self.assertEqual(manifest["repository"], "Mewplane/syauth")
            lines = (directory / "SHA256SUMS").read_text().splitlines()
            self.assertEqual(len(lines), len(module.required_artifacts("0.1.0")) + 1)
            for line in lines:
                digest, name = line.split("  ")
                self.assertEqual(digest, hashlib.sha256((directory / name).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
