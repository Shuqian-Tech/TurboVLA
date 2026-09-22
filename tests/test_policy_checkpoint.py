import unittest

import torch

from turbovla.evaluation.policy import _checkpoint_state_dict


class PolicyCheckpointTest(unittest.TestCase):
    def test_accepts_official_model_state_dict(self) -> None:
        state = {"weight": torch.ones(1)}
        self.assertIs(_checkpoint_state_dict({"model_state_dict": state}), state)

    def test_prefers_ema_state_dict(self) -> None:
        ema = {"weight": torch.ones(1)}
        raw = {"weight": torch.zeros(1)}
        self.assertIs(
            _checkpoint_state_dict({"ema_model_state_dict": ema, "model_state_dict": raw}),
            ema,
        )

    def test_rejects_checkpoint_without_model_weights(self) -> None:
        with self.assertRaises(KeyError):
            _checkpoint_state_dict({"model_config": {}})


if __name__ == "__main__":
    unittest.main()
