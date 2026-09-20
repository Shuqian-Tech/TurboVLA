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


if __name__ == "__main__":
    unittest.main()

