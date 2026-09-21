from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from turbovla.lite_hardware_pack import export_hardware_fixture


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "data" / "lite_hardware_e2e"


class LiteHardwarePackTest(unittest.TestCase):
    def test_checked_fixture_is_reproducible(self) -> None:
        expected = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            actual = export_hardware_fixture(Path(directory))
        self.assertEqual(actual["files"], expected["files"])
        self.assertEqual(actual["tensors"], expected["tensors"])
        self.assertEqual(actual["contract_version"], "0.2.0")

    def test_model_checksum_matches_manifest(self) -> None:
        manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256((FIXTURE / "model.bin").read_bytes()).hexdigest()
        self.assertEqual(digest, manifest["files"]["model.bin"])


if __name__ == "__main__":
    unittest.main()
