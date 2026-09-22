"""TurboVLA-Lite policy adapter for closed-loop LIBERO evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent

from . import policy as base
from .suite_policy import _array, _select_stats

LITE_IMAGE_SIZE = 128


class TurboVLALitePolicy:
    """Load a hardware-equivalent Lite checkpoint and expose LIBERO actions."""

    def __init__(
        self,
        *,
        ckpt_path: str | Path,
        stats_path: str | Path,
        stats_key: str | None = None,
        device: str = "cuda",
    ) -> None:
        self.ckpt_path = Path(ckpt_path)
        self.device = torch.device(device)
        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is unavailable; CPU inference fallback is prohibited")

        checkpoint = torch.load(self.ckpt_path, map_location="cpu", weights_only=False)
        if not isinstance(checkpoint, dict) or "state_dict" not in checkpoint or "config" not in checkpoint:
            raise ValueError("Lite checkpoint must contain state_dict and config")
        config = LiteStudentConfig(**checkpoint["config"])
        self.model = TurboVLALiteStudent(config, checkpoint.get("quantization"))
        self.model.load_state_dict(checkpoint["state_dict"], strict=True)
        self.model.to(self.device).eval()

        entries = checkpoint.get("instructions")
        if not isinstance(entries, list) or not entries:
            raise ValueError("Lite checkpoint must contain a non-empty instruction table")
        self.instruction_ids: dict[str, int] = {}
        for entry in entries:
            instruction = str(entry["text"])
            instruction_id = int(entry["instruction_id"])
            if instruction in self.instruction_ids:
                raise ValueError(f"duplicate Lite instruction: {instruction!r}")
            self.instruction_ids[instruction] = instruction_id

        stats_payload = json.loads(Path(stats_path).read_text(encoding="utf-8"))
        stats = _select_stats(stats_payload, stats_key)
        state_section = "proprio" if "proprio" in stats else "state"
        self.proprio_mean = _array(stats, state_section, "mean")
        self.proprio_std = _array(stats, state_section, "std")
        self.action_min = _array(stats, "action", "min")
        self.action_max = _array(stats, "action", "max")
        if self.proprio_mean.shape != (config.state_dim,):
            raise ValueError(f"state statistics must have shape ({config.state_dim},)")
        if self.action_min.shape != (config.action_dim,) or self.action_max.shape != (config.action_dim,):
            raise ValueError(f"action statistics must have shape ({config.action_dim},)")
        self.checkpoint_sha256 = hashlib.sha256(self.ckpt_path.read_bytes()).hexdigest()

    def _encode_state(self, state_or_obs: np.ndarray | dict[str, Any]) -> torch.Tensor:
        if isinstance(state_or_obs, dict):
            state = base.state_from_libero_obs(state_or_obs)
        else:
            state = np.asarray(state_or_obs, dtype=np.float32).reshape(-1)
        if state.shape != self.proprio_mean.shape:
            raise ValueError(f"Lite state must have shape {self.proprio_mean.shape}, got {state.shape}")
        normalized = (state - self.proprio_mean) / (self.proprio_std + 1.0e-6)
        encoded = np.clip(np.rint(normalized * 1024.0), -32768, 32767).astype(np.int16)
        return torch.from_numpy(encoded[None, :]).to(self.device)

    def _encode_image(self, primary_image: np.ndarray) -> torch.Tensor:
        image = np.asarray(primary_image)
        expected = (LITE_IMAGE_SIZE, LITE_IMAGE_SIZE, 3)
        if image.shape != expected:
            raise ValueError(f"Lite primary image must have shape {expected}, got {image.shape}")
        chw = np.ascontiguousarray(image.transpose(2, 0, 1)[None, None, ...], dtype=np.uint8)
        return torch.from_numpy(chw).to(self.device)

    def predict_normalized_action_chunk(
        self,
        primary_image: np.ndarray,
        wrist_image: np.ndarray,
        instruction: str,
        state_or_obs: np.ndarray | dict[str, Any],
    ) -> np.ndarray:
        del wrist_image
        if instruction not in self.instruction_ids:
            raise KeyError(f"instruction is absent from the Lite checkpoint table: {instruction!r}")
        image = self._encode_image(primary_image)
        state = self._encode_state(state_or_obs)
        instruction_id = torch.tensor([self.instruction_ids[instruction]], dtype=torch.long, device=self.device)
        with torch.inference_mode():
            action = self.model(image, state, instruction_id)["action"]
        return action[0].float().cpu().numpy()

    def _normalized_row_to_env_action(self, row: np.ndarray) -> np.ndarray:
        normalized = np.asarray(row, dtype=np.float32).reshape(-1)
        if normalized.shape != self.action_min.shape:
            raise ValueError(f"normalized action must have shape {self.action_min.shape}, got {normalized.shape}")
        arm = 0.5 * (normalized[:6] + 1.0) * (self.action_max[:6] - self.action_min[:6])
        arm += self.action_min[:6]
        gripper = np.asarray([base.gripper_command_from_norm(float(normalized[6]))], dtype=np.float32)
        return np.concatenate([arm, gripper]).astype(np.float32)

    def predict_env_action_chunk(
        self,
        primary_image: np.ndarray,
        wrist_image: np.ndarray,
        instruction: str,
        state_or_obs: np.ndarray | dict[str, Any],
        execute_steps: int | None = None,
    ) -> np.ndarray:
        normalized = self.predict_normalized_action_chunk(
            primary_image,
            wrist_image,
            instruction,
            state_or_obs,
        )
        actions = np.stack([self._normalized_row_to_env_action(row) for row in normalized])
        if execute_steps is not None:
            actions = actions[: int(execute_steps)]
        return actions


get_libero_dummy_action = base.get_libero_dummy_action
rotate_libero_image = base.rotate_libero_image
set_seed_everywhere = base.set_seed_everywhere
