"""Teacher-target caching and channel-independent token relation losses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import Dataset

CACHE_SCHEMA_VERSION = "1.0.0"


def token_relation_matrix(tokens: torch.Tensor) -> torch.Tensor:
    """Return cosine relations between tokens, independent of channel width."""

    if tokens.ndim != 3:
        raise ValueError(f"tokens must be [B,T,C], got {tuple(tokens.shape)}")
    normalized = F.normalize(tokens.float(), dim=-1, eps=1.0e-6)
    return normalized @ normalized.transpose(1, 2)


def pool_spatial_tokens(
    tokens: torch.Tensor,
    *,
    input_grid: tuple[int, int] = (16, 16),
    output_grid: tuple[int, int] = (4, 8),
) -> torch.Tensor:
    """Pool row-major spatial tokens without assuming a channel dimension."""

    if tokens.ndim != 3 or tokens.shape[1] != input_grid[0] * input_grid[1]:
        raise ValueError(
            f"tokens must be [B,{input_grid[0] * input_grid[1]},C], got {tuple(tokens.shape)}"
        )
    spatial = tokens.transpose(1, 2).reshape(tokens.shape[0], tokens.shape[2], *input_grid)
    return F.adaptive_avg_pool2d(spatial, output_grid).flatten(2).transpose(1, 2)


class TeacherDistillationCache:
    """Memory-mapped teacher targets aligned to one deterministic dataset index."""

    def __init__(self, root: str | Path, dataset: Any) -> None:
        self.root = Path(root)
        metadata_path = self.root / "metadata.json"
        if not metadata_path.is_file():
            raise FileNotFoundError(f"teacher cache metadata is missing: {metadata_path}")
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if self.metadata.get("schema_version") != CACHE_SCHEMA_VERSION:
            raise ValueError(f"unsupported teacher cache schema: {self.metadata.get('schema_version')!r}")
        if int(self.metadata.get("samples", -1)) != len(dataset):
            raise ValueError("teacher cache sample count does not match the dataset")
        if self.metadata.get("dataset_index_sha256") != dataset.index_sha256():
            raise ValueError("teacher cache index does not match the dataset split")

        self.actions = np.load(self.root / "teacher_action.npy", mmap_mode="r")
        self.visual_relations = np.load(self.root / "teacher_visual_relation.npy", mmap_mode="r")
        expected_actions = (len(dataset), 12, 7)
        expected_relations = (len(dataset), 32, 32)
        if self.actions.shape != expected_actions or self.visual_relations.shape != expected_relations:
            raise ValueError(
                "teacher cache tensors have invalid shapes: "
                f"action={self.actions.shape}, relation={self.visual_relations.shape}"
            )
        if self.actions.dtype != np.float16 or self.visual_relations.dtype != np.float16:
            raise ValueError("teacher cache tensors must use float16 storage")

    def __len__(self) -> int:
        return int(self.actions.shape[0])

    def __getitem__(self, item: int) -> dict[str, torch.Tensor]:
        return {
            "teacher_action": torch.from_numpy(np.array(self.actions[item], dtype=np.float32, copy=True)),
            "teacher_visual_relation": torch.from_numpy(
                np.array(self.visual_relations[item], dtype=np.float32, copy=True)
            ),
        }


class CachedDistillationDataset(Dataset):
    """Add aligned memory-mapped teacher targets to a base LIBERO dataset."""

    def __init__(self, dataset: Dataset, cache_root: str | Path) -> None:
        self.dataset = dataset
        self.cache = TeacherDistillationCache(cache_root, dataset)

    def __len__(self) -> int:
        return len(self.dataset)

    def __getitem__(self, item: int) -> dict:
        sample = dict(self.dataset[item])
        sample.update(self.cache[item])
        return sample
