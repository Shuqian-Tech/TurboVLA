from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from turbovla.lite_parameter_pack import export_parameter_pack, load_parameter_pack, reconstruct_reference_parameters
from turbovla.lite_reference import LiteParameters, load_contract
from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent


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

    def test_rejects_experimental_visual_encoder_checkpoint(self) -> None:
        config = replace(LiteStudentConfig.from_contract(load_contract()), visual_encoder="depthwise_separable")
        model = TurboVLALiteStudent(config)
        checkpoint = {"config": config.to_dict(), "state_dict": model.state_dict()}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "experimental visual encoders"):
                export_parameter_pack(None, Path(directory), checkpoint=checkpoint)

            mislabeled = {"config": {"visual_encoder": "pointwise"}, "state_dict": model.state_dict()}
            with self.assertRaisesRegex(ValueError, "experimental visual encoder weights"):
                export_parameter_pack(None, Path(directory), checkpoint=mislabeled)


if __name__ == "__main__":
    unittest.main()
