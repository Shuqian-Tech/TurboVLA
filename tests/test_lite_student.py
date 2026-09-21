from __future__ import annotations

import unittest

import torch

from turbovla.lite_reference import load_contract
from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent, lite_distillation_loss


class LiteStudentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = LiteStudentConfig.from_contract(load_contract())
        self.model = TurboVLALiteStudent(self.config, quantization=None)

    def test_fixed_forward_shapes(self) -> None:
        outputs = self.model(
            torch.zeros((2, 1, 3, 128, 128), dtype=torch.uint8),
            torch.zeros((2, 8), dtype=torch.int16),
            torch.zeros((2,), dtype=torch.long),
        )
        self.assertEqual(tuple(outputs["visual_tokens"].shape), (2, 32, 128))
        self.assertEqual(tuple(outputs["action"].shape), (2, 12, 7))

    def test_distillation_loss_is_finite(self) -> None:
        outputs = self.model(
            torch.zeros((2, 1, 3, 128, 128), dtype=torch.uint8),
            torch.zeros((2, 8), dtype=torch.int16),
            torch.zeros((2,), dtype=torch.long),
        )
        targets = torch.zeros((2, 12, 7))
        features = torch.zeros((2, 32, 128))
        loss, metrics = lite_distillation_loss(outputs, targets, targets, features, self.config)
        self.assertTrue(torch.isfinite(loss))
        self.assertIn("teacher_action_l1", metrics)

    def test_qat_forward_quantizes_hardware_weights_without_extra_fusion_biases(self) -> None:
        calibration = {
            "activations": {"image_normalized": 0.02, "visual_conv": 0.01},
            "weights": {
                "conv_weight": 0.01,
                "visual_projection": 0.01,
                "fusion_visual": 0.01,
                "fusion_language": 0.01,
                "fusion_gate": 0.01,
                "state_projection": 0.01,
                "action_input": 0.01,
                "action_output": 0.01,
            },
        }
        model = TurboVLALiteStudent(self.config, calibration)
        self.assertIsNone(model.fusion_language[0].bias)
        self.assertIsNone(model.fusion_gate[0].bias)
        outputs = model(
            torch.zeros((1, 1, 3, 128, 128), dtype=torch.uint8),
            torch.zeros((1, 8), dtype=torch.int16),
            torch.zeros((1,), dtype=torch.long),
        )
        self.assertTrue(torch.isfinite(outputs["action"]).all())


if __name__ == "__main__":
    unittest.main()
