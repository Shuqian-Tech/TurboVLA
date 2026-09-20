from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from turbovla.lite_parameter_pack import export_parameter_pack, load_parameter_pack, reconstruct_reference_parameters
from turbovla.lite_reference import LiteParameters, load_contract


class LiteParameterPackTest(unittest.TestCase):
    def test_aligned_round_trip_reconstructs_reference_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            original = LiteParameters.deterministic(load_contract())
            manifest = export_parameter_pack(original, output)
            self.assertEqual(manifest["alignment_bytes"], 64)
            self.assertTrue(all(entry["offset"] % 64 == 0 for entry in manifest["tensors"]))
            loaded = load_parameter_pack(output)
            self.assertEqual(loaded["instruction_table"].shape, (256, 128))
            reconstructed = reconstruct_reference_parameters(output)
            self.assertEqual(reconstructed.action_output.shape, original.action_output.shape)


if __name__ == "__main__":
    unittest.main()
