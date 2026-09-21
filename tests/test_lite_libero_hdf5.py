from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import torch

from turbovla.data.lite_libero_hdf5 import LiberoHdf5LiteDataset


class LiteLiberoHdf5Test(unittest.TestCase):
    def _write_fixture(self, root: Path) -> tuple[Path, Path]:
        dataset_dir = root / "libero_spatial"
        dataset_dir.mkdir()
        dataset_path = dataset_dir / "task_demo.hdf5"
        with h5py.File(dataset_path, "w") as handle:
            data = handle.create_group("data")
            data.attrs["problem_info"] = json.dumps({"language_instruction": "move the object"})
            for demo_index in range(12):
                demo = data.create_group(f"demo_{demo_index}")
                actions = np.zeros((4, 7), dtype=np.float32)
                actions[:, 0] = [0.1, 0.2, 0.0, 0.3]
                actions[:, 6] = [-1.0, -1.0, -1.0, 1.0]
                demo.create_dataset("actions", data=actions)
                obs = demo.create_group("obs")
                images = np.zeros((4, 128, 128, 3), dtype=np.uint8)
                images[:, 0, 0, 0] = 11
                images[:, -1, -1, 0] = 22
                obs.create_dataset("agentview_rgb", data=images)
                obs.create_dataset("ee_states", data=np.zeros((4, 6), dtype=np.float32))
                obs.create_dataset("gripper_states", data=np.zeros((4, 2), dtype=np.float32))
        stats_path = root / "stats.json"
        stats_path.write_text(
            json.dumps(
                {
                    "test": {
                        "proprio": {"mean": [0.0] * 8, "std": [1.0] * 8},
                        "action": {"min": [-1.0] * 7, "max": [1.0] * 7},
                    }
                }
            ),
            encoding="utf-8",
        )
        return dataset_dir, stats_path

    def test_contract_shapes_split_and_noop_filter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_dir, stats_path = self._write_fixture(Path(directory))
            train = LiberoHdf5LiteDataset(
                dataset_dir, stats_path, stats_key="test", split="train", validation_fraction=0.25, seed=7
            )
            validation = LiberoHdf5LiteDataset(
                dataset_dir, stats_path, stats_key="test", split="validation", validation_fraction=0.25, seed=7
            )
            self.assertGreater(len(train), 0)
            self.assertGreater(len(validation), 0)
            self.assertEqual(len(train) + len(validation), 36)
            sample = train[0]
            self.assertEqual(tuple(sample["image"].shape), (1, 3, 128, 128))
            self.assertEqual(sample["image"].dtype, torch.uint8)
            self.assertEqual(tuple(sample["state"].shape), (8,))
            self.assertEqual(tuple(sample["action_target"].shape), (12, 7))
            self.assertEqual(int(sample["instruction_id"]), 0)
            self.assertEqual(int(sample["image"][0, 0, 0, 0]), 22)


if __name__ == "__main__":
    unittest.main()
