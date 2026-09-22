import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from turbovla.evaluation.lite_suite_policy import TurboVLALitePolicy
from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent


class LiteSuitePolicyTests(unittest.TestCase):
    def _artifacts(self, root: Path) -> tuple[Path, Path]:
        config = LiteStudentConfig(fake_quant=False)
        model = TurboVLALiteStudent(config)
        for parameter in model.parameters():
            parameter.data.zero_()
        checkpoint = root / "lite.pt"
        torch.save(
            {
                "state_dict": model.state_dict(),
                "config": config.to_dict(),
                "quantization": None,
                "instructions": [{"instruction_id": 3, "text": "move the bowl"}],
            },
            checkpoint,
        )
        stats = root / "stats.json"
        stats.write_text(
            json.dumps(
                {
                    "suite": {
                        "proprio": {"mean": [0.0] * 8, "std": [1.0] * 8},
                        "action": {
                            "min": [-1.0, -2.0, -3.0, -0.4, -0.5, -0.6, -1.0],
                            "max": [1.0, 2.0, 3.0, 0.4, 0.5, 0.6, 1.0],
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        return checkpoint, stats

    def test_predicts_hardware_shape_and_denormalizes_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint, stats = self._artifacts(Path(directory))
            policy = TurboVLALitePolicy(
                ckpt_path=checkpoint,
                stats_path=stats,
                stats_key="suite",
                device="cpu",
            )
            obs = {
                "robot0_eef_pos": np.zeros(3, dtype=np.float32),
                "robot0_eef_quat": np.asarray([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
                "robot0_gripper_qpos": np.zeros(2, dtype=np.float32),
            }
            actions = policy.predict_env_action_chunk(
                np.zeros((128, 128, 3), dtype=np.uint8),
                np.zeros((128, 128, 3), dtype=np.uint8),
                "move the bowl",
                obs,
                execute_steps=2,
            )
            self.assertEqual(actions.shape, (2, 7))
            np.testing.assert_allclose(actions[:, :6], 0.0, atol=1.0e-6)
            np.testing.assert_array_equal(actions[:, 6], 1.0)

    def test_rejects_unknown_instruction_and_wrong_image_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint, stats = self._artifacts(Path(directory))
            policy = TurboVLALitePolicy(
                ckpt_path=checkpoint,
                stats_path=stats,
                stats_key="suite",
                device="cpu",
            )
            state = np.zeros(8, dtype=np.float32)
            image = np.zeros((128, 128, 3), dtype=np.uint8)
            with self.assertRaises(KeyError):
                policy.predict_normalized_action_chunk(image, image, "unknown", state)
            with self.assertRaises(ValueError):
                policy.predict_normalized_action_chunk(image[:64], image, "move the bowl", state)


if __name__ == "__main__":
    unittest.main()
