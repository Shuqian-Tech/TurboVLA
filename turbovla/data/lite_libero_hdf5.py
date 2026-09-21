"""Hardware-contract LIBERO HDF5 samples for TurboVLA-Lite training."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
import torch
from torch.utils.data import Dataset


@dataclass(frozen=True)
class LiteSampleIndex:
    file_index: int
    demo_name: str
    step_position: int


def _sorted_demos(group: h5py.Group) -> list[str]:
    return sorted(group.keys(), key=lambda name: int(name.rsplit("_", 1)[1]))


def _is_noop(action: np.ndarray, previous_action: np.ndarray | None, threshold: float = 1.0e-4) -> bool:
    arm_is_still = float(np.linalg.norm(action[:-1])) < threshold
    if previous_action is None:
        return arm_is_still
    return arm_is_still and float(action[-1]) == float(previous_action[-1])


def _kept_steps(actions: np.ndarray) -> tuple[int, ...]:
    kept: list[int] = []
    previous_action: np.ndarray | None = None
    for step, action in enumerate(actions):
        if _is_noop(action, previous_action):
            continue
        kept.append(step)
        previous_action = action
    return tuple(kept)


def _demo_is_validation(file_name: str, demo_name: str, seed: int, fraction: float) -> bool:
    digest = hashlib.sha256(f"{seed}:{file_name}:{demo_name}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "little") / float(1 << 64)
    return bucket < fraction


class LiberoHdf5LiteDataset(Dataset):
    """Map-style, trajectory-split view of official LIBERO HDF5 demonstrations."""

    def __init__(
        self,
        dataset_dir: str | Path,
        stats_path: str | Path,
        *,
        stats_key: str = "libero_all4_no_noops",
        split: str = "train",
        validation_fraction: float = 0.2,
        seed: int = 20260921,
        action_horizon: int = 12,
        rotate_images: bool = True,
        include_teacher_observations: bool = False,
    ) -> None:
        if split not in {"train", "validation", "all"}:
            raise ValueError("split must be train, validation, or all")
        if not 0.0 <= validation_fraction < 1.0:
            raise ValueError("validation_fraction must be in [0, 1)")
        self.dataset_dir = Path(dataset_dir)
        self.files = sorted(self.dataset_dir.glob("*.hdf5"))
        if not self.files:
            raise FileNotFoundError(f"no HDF5 files found in {self.dataset_dir}")
        self.split = split
        self.validation_fraction = float(validation_fraction)
        self.seed = int(seed)
        self.action_horizon = int(action_horizon)
        self.rotate_images = bool(rotate_images)
        self.include_teacher_observations = bool(include_teacher_observations)
        if self.action_horizon < 1:
            raise ValueError("action_horizon must be positive")

        payload = json.loads(Path(stats_path).read_text(encoding="utf-8"))
        if stats_key not in payload:
            raise KeyError(f"stats key {stats_key!r} is absent from {stats_path}")
        stats = payload[stats_key]
        state_stats = stats["proprio"] if "proprio" in stats else stats["state"]
        self.state_mean = np.asarray(state_stats["mean"], dtype=np.float32)
        self.state_std = np.asarray(state_stats["std"], dtype=np.float32)
        self.action_min = np.asarray(stats["action"]["min"], dtype=np.float32)
        self.action_max = np.asarray(stats["action"]["max"], dtype=np.float32)
        if self.state_mean.shape != (8,) or self.action_min.shape != (7,):
            raise ValueError("Lite LIBERO statistics must have state_dim=8 and action_dim=7")

        self.instructions: list[str] = []
        self.instruction_ids: dict[str, int] = {}
        self._kept_by_demo: dict[tuple[int, str], tuple[int, ...]] = {}
        self._samples: list[LiteSampleIndex] = []
        self._handles: dict[int, h5py.File] = {}
        self._scan()
        if not self._samples:
            raise ValueError(f"split {split!r} produced no samples from {self.dataset_dir}")

    def _scan(self) -> None:
        for file_index, path in enumerate(self.files):
            with h5py.File(path, "r") as handle:
                data = handle["data"]
                problem = json.loads(data.attrs["problem_info"])
                instruction = str(problem["language_instruction"])
                instruction_id = len(self.instructions)
                if instruction_id >= 256:
                    raise ValueError("instruction table exceeds the 256-entry hardware contract")
                self.instructions.append(instruction)
                self.instruction_ids[path.name] = instruction_id
                for demo_name in _sorted_demos(data):
                    is_validation = _demo_is_validation(path.name, demo_name, self.seed, self.validation_fraction)
                    if self.split == "train" and is_validation:
                        continue
                    if self.split == "validation" and not is_validation:
                        continue
                    actions = np.asarray(data[demo_name]["actions"], dtype=np.float32)
                    kept = _kept_steps(actions)
                    self._kept_by_demo[(file_index, demo_name)] = kept
                    self._samples.extend(
                        LiteSampleIndex(file_index, demo_name, position) for position in range(len(kept))
                    )

    def __len__(self) -> int:
        return len(self._samples)

    def __getstate__(self) -> dict:
        state = self.__dict__.copy()
        state["_handles"] = {}
        return state

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()

    def _handle(self, file_index: int) -> h5py.File:
        if file_index not in self._handles:
            self._handles[file_index] = h5py.File(self.files[file_index], "r")
        return self._handles[file_index]

    def _encode_state(self, state: np.ndarray) -> np.ndarray:
        normalized = (state.astype(np.float32) - self.state_mean) / (self.state_std + 1.0e-6)
        return np.clip(np.rint(normalized * 1024.0), -32768, 32767).astype(np.int16)

    def _normalize_actions(self, actions: np.ndarray) -> np.ndarray:
        normalized = actions.astype(np.float32, copy=True)
        normalized[:, :6] = (
            2.0
            * (normalized[:, :6] - self.action_min[None, :6])
            / (self.action_max[None, :6] - self.action_min[None, :6] + 1.0e-6)
            - 1.0
        )
        normalized[:, :6] = np.clip(normalized[:, :6], -1.0, 1.0)
        normalized[:, 6] = np.clip(normalized[:, 6], -1.0, 1.0)
        return normalized

    def __getitem__(self, item: int) -> dict[str, torch.Tensor | str]:
        sample = self._samples[item]
        kept = self._kept_by_demo[(sample.file_index, sample.demo_name)]
        raw_step = kept[sample.step_position]
        future = kept[sample.step_position : sample.step_position + self.action_horizon]
        valid_length = len(future)
        if valid_length < self.action_horizon:
            future = future + (future[-1],) * (self.action_horizon - valid_length)

        demo = self._handle(sample.file_index)["data"][sample.demo_name]
        image = np.asarray(demo["obs"]["agentview_rgb"][raw_step], dtype=np.uint8)
        if image.shape != (128, 128, 3):
            raise ValueError(f"expected a 128x128 RGB image, got {image.shape}")
        if self.rotate_images:
            image = image[::-1, ::-1]
        image = np.ascontiguousarray(image.transpose(2, 0, 1)[None, ...])

        state = np.concatenate(
            [
                np.asarray(demo["obs"]["ee_states"][raw_step], dtype=np.float32),
                np.asarray(demo["obs"]["gripper_states"][raw_step], dtype=np.float32),
            ]
        )
        demo_actions = np.asarray(demo["actions"], dtype=np.float32)
        actions = self._normalize_actions(demo_actions[list(future)])
        mask = np.zeros(self.action_horizon, dtype=np.float32)
        mask[:valid_length] = 1.0
        file_name = self.files[sample.file_index].name
        result: dict[str, torch.Tensor | str] = {
            "image": torch.from_numpy(image),
            "state": torch.from_numpy(self._encode_state(state)),
            "instruction_id": torch.tensor(self.instruction_ids[file_name], dtype=torch.long),
            "instruction": self.instructions[self.instruction_ids[file_name]],
            "action_target": torch.from_numpy(actions),
            "action_mask": torch.from_numpy(mask),
            "task_name": self.files[sample.file_index].stem.removesuffix("_demo"),
        }
        if self.include_teacher_observations:
            wrist = np.asarray(demo["obs"]["eye_in_hand_rgb"][raw_step], dtype=np.uint8)
            if wrist.shape != (128, 128, 3):
                raise ValueError(f"expected a 128x128 wrist RGB image, got {wrist.shape}")
            if self.rotate_images:
                wrist = wrist[::-1, ::-1]
            result["teacher_wrist_image"] = torch.from_numpy(
                np.ascontiguousarray(wrist.transpose(2, 0, 1))
            )
            result["teacher_raw_state"] = torch.from_numpy(state.astype(np.float32, copy=False))
        return result

    def index_sha256(self) -> str:
        digest = hashlib.sha256()
        for sample in self._samples:
            raw_step = self._kept_by_demo[(sample.file_index, sample.demo_name)][sample.step_position]
            identity = f"{self.files[sample.file_index].name}\0{sample.demo_name}\0{raw_step}\n"
            digest.update(identity.encode("utf-8"))
        return digest.hexdigest()

    def manifest(self) -> dict:
        return {
            "dataset_dir": str(self.dataset_dir.resolve()),
            "files": [{"name": path.name, "bytes": path.stat().st_size} for path in self.files],
            "split": self.split,
            "validation_fraction": self.validation_fraction,
            "split_seed": self.seed,
            "samples": len(self),
            "index_sha256": self.index_sha256(),
            "instructions": [
                {"instruction_id": index, "text": instruction}
                for index, instruction in enumerate(self.instructions)
            ],
            "action_horizon": self.action_horizon,
            "noop_filter": "arm_l2_lt_1e-4_and_unchanged_gripper",
            "rotate_images_180_degrees": self.rotate_images,
        }
