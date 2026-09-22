from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from turbovla.distillation import (
    CACHE_SCHEMA_VERSION,
    CachedDistillationDataset,
    pool_spatial_tokens,
    token_relation_matrix,
)


class _BaseDataset(Dataset):
    def __len__(self) -> int:
        return 2

    def __getitem__(self, item: int) -> dict:
        return {"item": torch.tensor(item)}

    @staticmethod
    def index_sha256() -> str:
        return "a" * 64


class DistillationTest(unittest.TestCase):
    def test_pool_and_relation_are_channel_independent(self) -> None:
        tokens = torch.arange(2 * 256 * 5, dtype=torch.float32).reshape(2, 256, 5)
        pooled = pool_spatial_tokens(tokens)
        relation = token_relation_matrix(pooled)
        self.assertEqual(tuple(pooled.shape), (2, 32, 5))
        self.assertEqual(tuple(relation.shape), (2, 32, 32))
        self.assertTrue(torch.isfinite(relation).all())
        self.assertTrue(torch.allclose(relation, relation.transpose(1, 2)))

    def test_memory_mapped_cache_is_index_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            np.save(root / "teacher_action.npy", np.zeros((2, 12, 7), dtype=np.float16))
            np.save(root / "teacher_visual_relation.npy", np.zeros((2, 32, 32), dtype=np.float16))
            (root / "metadata.json").write_text(
                json.dumps(
                    {
                        "schema_version": CACHE_SCHEMA_VERSION,
                        "samples": 2,
                        "dataset_index_sha256": "a" * 64,
                    }
                ),
                encoding="utf-8",
            )
            dataset = CachedDistillationDataset(_BaseDataset(), root)
            sample = dataset[1]
            self.assertEqual(tuple(sample["teacher_action"].shape), (12, 7))
            self.assertEqual(tuple(sample["teacher_visual_relation"].shape), (32, 32))
            (root / "metadata.json").write_text(
                json.dumps(
                    {
                        "schema_version": CACHE_SCHEMA_VERSION,
                        "samples": 2,
                        "dataset_index_sha256": "b" * 64,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "index does not match"):
                CachedDistillationDataset(_BaseDataset(), root)


if __name__ == "__main__":
    unittest.main()
