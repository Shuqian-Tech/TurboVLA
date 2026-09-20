"""Deterministic TurboVLA-Lite FP32 and INT8 software reference.

The reference is intentionally small and NumPy-only so it can be used to
produce golden tensors without a framework runtime.  Interface dimensions and
error values are loaded from the hardware contract; the Lite internal layer
sizes live in :class:`LiteArchitecture` in one place.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "hardware" / "contracts" / "turbovla_lite_contract.json"


class ReferenceInputError(ValueError):
    """Input error carrying the contract error code used by runtime tests."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = int(code)


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@dataclass(frozen=True)
class LiteArchitecture:
    """Fixed internal dimensions for the FPGA-friendly student network."""

    conv_channels: int = 16
    token_rows: int = 4
    token_cols: int = 8
    action_hidden: int = 64
    instruction_table_size: int = 256
    state_normalization: float = 1.0 / 1024.0


@dataclass
class LiteParameters:
    conv_weight: np.ndarray
    conv_bias: np.ndarray
    visual_projection: np.ndarray
    visual_bias: np.ndarray
    instruction_table: np.ndarray
    fusion_visual: np.ndarray
    fusion_language: np.ndarray
    fusion_gate: np.ndarray
    fusion_bias: np.ndarray
    state_projection: np.ndarray
    state_bias: np.ndarray
    action_input: np.ndarray
    action_input_bias: np.ndarray
    action_output: np.ndarray
    action_output_bias: np.ndarray

    @classmethod
    def deterministic(
        cls,
        contract: Mapping,
        architecture: LiteArchitecture = LiteArchitecture(),
        seed: int = 20260919,
    ) -> "LiteParameters":
        """Create reproducible parameters for tests and golden generation.

        T003 replaces these arrays with a trained checkpoint.  Keeping the
        seed and shapes stable lets T002 exercise the complete data path now.
        """

        hidden = int(contract["fusion"]["hidden_dim"])
        action_dim = int(contract["action"]["shape"][-1])
        horizon = int(contract["action"]["shape"][-2])
        state_dim = int(contract["state"]["shape"][-1])
        rng = np.random.default_rng(seed)

        def normal(shape: tuple[int, ...], scale: float = 0.05) -> np.ndarray:
            return rng.normal(0.0, scale, size=shape).astype(np.float32)

        return cls(
            conv_weight=normal((architecture.conv_channels, 3)),
            conv_bias=np.zeros((architecture.conv_channels,), dtype=np.float32),
            visual_projection=normal((architecture.conv_channels, hidden)),
            visual_bias=np.zeros((hidden,), dtype=np.float32),
            instruction_table=normal((architecture.instruction_table_size, hidden)),
            fusion_visual=normal((2, hidden, hidden)),
            fusion_language=normal((2, hidden, hidden)),
            fusion_gate=normal((2, hidden, hidden)),
            fusion_bias=np.zeros((2, hidden), dtype=np.float32),
            state_projection=normal((state_dim, hidden)),
            state_bias=np.zeros((hidden,), dtype=np.float32),
            action_input=normal((hidden, architecture.action_hidden)),
            action_input_bias=np.zeros((architecture.action_hidden,), dtype=np.float32),
            action_output=normal((architecture.action_hidden, horizon * action_dim)),
            action_output_bias=np.zeros((horizon * action_dim,), dtype=np.float32),
        )

    def arrays(self) -> dict[str, np.ndarray]:
        return {name: value for name, value in vars(self).items() if isinstance(value, np.ndarray)}


@dataclass(frozen=True)
class LiteQuantization:
    """Per-tensor symmetric scales used by the INT8 replay."""

    activations: Mapping[str, float]
    weights: Mapping[str, float]
    state_normalization: float = 1.0 / 1024.0
    state_input: float = 1.0 / 127.0

    @staticmethod
    def _scale(value: np.ndarray) -> float:
        maximum = float(np.max(np.abs(value)))
        return max(maximum / 127.0, 1.0e-6)

    @classmethod
    def from_fp32(
        cls,
        parameters: LiteParameters,
        traces: Mapping[str, np.ndarray],
        state_normalization: float = 1.0 / 1024.0,
    ) -> "LiteQuantization":
        weights = {name: cls._scale(value) for name, value in parameters.arrays().items()}
        activations = {name: cls._scale(value) for name, value in traces.items()}
        return cls(activations=activations, weights=weights, state_normalization=state_normalization)

    def to_dict(self) -> dict:
        return {
            "activations": {name: float(value) for name, value in self.activations.items()},
            "weights": {name: float(value) for name, value in self.weights.items()},
            "state_normalization": float(self.state_normalization),
            "state_input": float(self.state_input),
        }


def _quantize(value: np.ndarray, scale: float, dtype=np.int8) -> np.ndarray:
    limit = np.iinfo(dtype).max
    return np.clip(np.rint(value / scale), -limit - 1, limit).astype(dtype)


def _dequantize(value: np.ndarray, scale: float) -> np.ndarray:
    return value.astype(np.float32) * np.float32(scale)


def _relu(value: np.ndarray) -> np.ndarray:
    return np.maximum(value, 0.0).astype(np.float32)


def _sigmoid(value: np.ndarray) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-np.clip(value, -12.0, 12.0)))).astype(np.float32)


def _validate_inputs(contract: Mapping, image: np.ndarray, state: np.ndarray, instruction_id: np.ndarray) -> None:
    image_shape = tuple(contract["image"]["shape"])
    if image.shape != image_shape or image.dtype != np.uint8:
        code = contract["errors"]["invalid_buffer"]
        raise ReferenceInputError(code, f"image must be uint8 {image_shape}, got {image.dtype} {image.shape}")
    state_shape = tuple(contract["state"]["shape"])
    if state.shape != state_shape or state.dtype != np.int16:
        code = contract["errors"]["invalid_buffer"]
        raise ReferenceInputError(code, f"state must be int16 {state_shape}, got {state.dtype} {state.shape}")
    if instruction_id.shape != tuple(contract["language"]["input"]["shape"]) or instruction_id.dtype != np.uint16:
        code = contract["errors"]["invalid_instruction_id"]
        raise ReferenceInputError(code, "instruction_id must be uint16 [1]")


class TurboVLALiteReference:
    """FP32 and quantized inference with identical fixed tensor boundaries."""

    def __init__(
        self,
        contract: Mapping | None = None,
        parameters: LiteParameters | None = None,
        quantization: LiteQuantization | None = None,
        architecture: LiteArchitecture = LiteArchitecture(),
    ) -> None:
        self.contract = dict(contract or load_contract())
        self.architecture = architecture
        self.parameters = parameters or LiteParameters.deterministic(self.contract, architecture)
        self.quantization = quantization
        self._validate_contract()

    def _validate_contract(self) -> None:
        if self.contract["batch_size"] != 1 or self.contract["views"] != 1:
            raise ValueError("TurboVLA-Lite reference only supports batch=1 and view=1")
        if self.contract["fusion"]["hidden_dim"] != 128:
            raise ValueError("Lite reference expects the contract hidden_dim to remain 128")
        if tuple(self.contract["visual_tokens"]["shape"]) != (1, 32, 128):
            raise ValueError("Lite reference expects 32 visual tokens of width 128")

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        image_spec = self.contract["image"]
        image_float = image.astype(np.float32) / 255.0
        mean = np.asarray(image_spec["preprocess"]["mean"], dtype=np.float32).reshape(1, 1, 3, 1, 1)
        std = np.asarray(image_spec["preprocess"]["std"], dtype=np.float32).reshape(1, 1, 3, 1, 1)
        return ((image_float - mean) / std).astype(np.float32)

    def _visual_fp32(self, normalized: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        p = self.parameters
        conv = np.einsum("nvchw,oc->nvohw", normalized, p.conv_weight) + p.conv_bias[None, None, :, None, None]
        conv = _relu(conv)
        _, _, channels, height, width = conv.shape
        rows, cols = self.architecture.token_rows, self.architecture.token_cols
        pooled = conv.reshape(1, 1, channels, rows, height // rows, cols, width // cols).mean(axis=(4, 6))
        pooled = pooled.transpose(0, 1, 3, 4, 2).reshape(1, 1, rows * cols, channels)
        tokens = _relu(pooled @ p.visual_projection + p.visual_bias)
        return conv, tokens[:, 0]

    def _fusion_fp32(self, visual: np.ndarray, language: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
        p = self.parameters
        traces: list[np.ndarray] = []
        fused = visual
        for layer in range(2):
            candidate = fused @ p.fusion_visual[layer] + language @ p.fusion_language[layer][:, :]
            candidate = candidate + p.fusion_bias[layer]
            gate_logits = fused @ p.fusion_gate[layer] + language[:, None, :] @ p.fusion_gate[layer]
            gate = _sigmoid(gate_logits)
            fused = ((1.0 - gate) * fused + gate * np.tanh(candidate)).astype(np.float32)
            traces.append(fused)
        return fused, traces

    def _fp32(self, image: np.ndarray, state: np.ndarray, instruction_id: np.ndarray) -> dict[str, np.ndarray]:
        normalized = self._preprocess(image)
        visual_conv, visual = self._visual_fp32(normalized)
        language = self.parameters.instruction_table[instruction_id.astype(np.int64)]
        fused, fusion_traces = self._fusion_fp32(visual, language)
        state_float = state.astype(np.float32) * self.architecture.state_normalization
        pooled = _relu(fused.mean(axis=1) + state_float @ self.parameters.state_projection + self.parameters.state_bias)
        hidden = _relu(pooled @ self.parameters.action_input + self.parameters.action_input_bias)
        logits = hidden @ self.parameters.action_output + self.parameters.action_output_bias
        action = np.tanh(logits.reshape(self.contract["action"]["shape"])).astype(np.float32)
        return {
            "image_normalized": normalized,
            "visual_conv": visual_conv,
            "visual_tokens": visual,
            "language_embedding": language,
            "fusion_0": fusion_traces[0],
            "fusion_1": fusion_traces[1],
            "state_projection": pooled,
            "action_hidden": hidden,
            "action": action,
        }

    def _require_quantization(self, fp32_traces: Mapping[str, np.ndarray]) -> LiteQuantization:
        if self.quantization is not None:
            return self.quantization
        self.quantization = LiteQuantization.from_fp32(
            self.parameters, fp32_traces, state_normalization=self.architecture.state_normalization
        )
        return self.quantization

    def _int8(
        self, image: np.ndarray, state: np.ndarray, instruction_id: np.ndarray, q: LiteQuantization
    ) -> dict[str, np.ndarray]:
        p = self.parameters

        def qa(name, value):
            return _quantize(value, q.activations[name])

        def qw(name, value):
            return _quantize(value, q.weights[name])

        normalized = self._preprocess(image)
        image_q = qa("image_normalized", normalized)
        conv_acc = np.einsum(
            "nvchw,oc->nvohw", image_q.astype(np.int32), qw("conv_weight", p.conv_weight).astype(np.int32)
        )
        conv = _relu(
            _dequantize(conv_acc, q.activations["image_normalized"] * q.weights["conv_weight"])
            + p.conv_bias[None, None, :, None, None]
        )
        conv_q = qa("visual_conv", conv)
        _, _, channels, height, width = conv_q.shape
        rows, cols = self.architecture.token_rows, self.architecture.token_cols
        pooled_q = conv_q.reshape(1, 1, channels, rows, height // rows, cols, width // cols).mean(axis=(4, 6))
        pooled_q = pooled_q.transpose(0, 1, 3, 4, 2).reshape(1, rows * cols, channels).astype(np.int8)
        visual_acc = np.matmul(pooled_q.astype(np.int32), qw("visual_projection", p.visual_projection).astype(np.int32))
        visual = _relu(
            _dequantize(visual_acc, q.activations["visual_conv"] * q.weights["visual_projection"]) + p.visual_bias
        )
        visual_q = qa("visual_tokens", visual)
        language_q = _quantize(
            p.instruction_table[instruction_id.astype(np.int64)], q.activations["language_embedding"]
        )
        fused_q = visual_q
        fusion_traces: list[np.ndarray] = []
        for layer in range(2):
            input_scale_name = "visual_tokens" if layer == 0 else "fusion_0"
            output_scale_name = "fusion_0" if layer == 0 else "fusion_1"
            input_scale = q.activations[input_scale_name]
            visual_part = np.matmul(
                fused_q.astype(np.int32), qw("fusion_visual", p.fusion_visual[layer]).astype(np.int32)
            )
            language_part = np.matmul(
                language_q.astype(np.int32), qw("fusion_language", p.fusion_language[layer]).astype(np.int32)
            )
            candidate = _dequantize(visual_part, input_scale * q.weights["fusion_visual"])
            candidate += _dequantize(language_part, q.activations["language_embedding"] * q.weights["fusion_language"])[
                :, None, :
            ]
            candidate += p.fusion_bias[layer]
            gate_part = np.matmul(fused_q.astype(np.int32), qw("fusion_gate", p.fusion_gate[layer]).astype(np.int32))
            language_gate = np.matmul(
                language_q.astype(np.int32), qw("fusion_gate", p.fusion_gate[layer]).astype(np.int32)
            )
            gate = _sigmoid(
                _dequantize(gate_part, input_scale * q.weights["fusion_gate"])
                + _dequantize(language_gate, q.activations["language_embedding"] * q.weights["fusion_gate"])[
                    ..., None, :
                ]
            )
            fused = ((1.0 - gate) * _dequantize(fused_q, input_scale) + gate * np.tanh(candidate)).astype(np.float32)
            fused_q = qa(output_scale_name, fused)
            fusion_traces.append(_dequantize(fused_q, q.activations[output_scale_name]))
        state_q = _quantize(state.astype(np.float32) * q.state_normalization, q.state_input)
        pooled = np.mean(fused_q.astype(np.float32) * q.activations["fusion_1"], axis=1)
        state_acc = np.matmul(state_q.astype(np.int32), qw("state_projection", p.state_projection).astype(np.int32))
        pooled = _relu(pooled + _dequantize(state_acc, q.state_input * q.weights["state_projection"]) + p.state_bias)
        pooled_q = qa("state_projection", pooled)
        hidden_acc = np.matmul(pooled_q.astype(np.int32), qw("action_input", p.action_input).astype(np.int32))
        hidden = _relu(
            _dequantize(hidden_acc, q.activations["state_projection"] * q.weights["action_input"]) + p.action_input_bias
        )
        hidden_q = qa("action_hidden", hidden)
        logits_acc = np.matmul(hidden_q.astype(np.int32), qw("action_output", p.action_output).astype(np.int32))
        logits = (
            _dequantize(logits_acc, q.activations["action_hidden"] * q.weights["action_output"]) + p.action_output_bias
        )
        action = np.tanh(logits.reshape(self.contract["action"]["shape"])).astype(np.float32)
        return {
            "image_normalized": _dequantize(image_q, q.activations["image_normalized"]),
            "visual_conv": _dequantize(conv_q, q.activations["visual_conv"]),
            "visual_tokens": _dequantize(visual_q, q.activations["visual_tokens"]),
            "language_embedding": _dequantize(language_q, q.activations["language_embedding"]),
            "fusion_0": fusion_traces[0],
            "fusion_1": fusion_traces[1],
            "state_projection": _dequantize(pooled_q, q.activations["state_projection"]),
            "action_hidden": _dequantize(hidden_q, q.activations["action_hidden"]),
            "action": action,
        }

    def run(
        self, image: np.ndarray, state: np.ndarray, instruction_id: np.ndarray, mode: str = "fp32"
    ) -> dict[str, np.ndarray]:
        _validate_inputs(self.contract, image, state, instruction_id)
        invalid = int(self.contract["language"]["input"]["invalid_value"])
        ids = instruction_id.astype(np.int64)
        if np.any(ids == invalid) or np.any(ids >= self.architecture.instruction_table_size):
            raise ReferenceInputError(
                self.contract["errors"]["invalid_instruction_id"], "instruction_id is not in the embedding table"
            )
        fp32_traces = self._fp32(image, state, instruction_id)
        if mode == "fp32":
            return fp32_traces
        if mode == "int8":
            return self._int8(image, state, instruction_id, self._require_quantization(fp32_traces))
        raise ValueError("mode must be 'fp32' or 'int8'")

    def compare(self, image: np.ndarray, state: np.ndarray, instruction_id: np.ndarray) -> dict[str, dict[str, float]]:
        fp32 = self.run(image, state, instruction_id, mode="fp32")
        int8 = self.run(image, state, instruction_id, mode="int8")
        result: dict[str, dict[str, float]] = {}
        for name in fp32:
            delta = np.abs(fp32[name] - int8[name])
            result[name] = {
                "max_abs_error": float(np.max(delta)),
                "mean_abs_error": float(np.mean(delta)),
                "fp32_sha256": hashlib.sha256(fp32[name].tobytes()).hexdigest(),
                "int8_sha256": hashlib.sha256(int8[name].tobytes()).hexdigest(),
            }
        return result


def deterministic_sample(contract: Mapping | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return one stable input sample used by tests and golden generation."""

    image = np.arange(128 * 128 * 3, dtype=np.uint32).reshape(1, 1, 3, 128, 128)
    image = (image % 256).astype(np.uint8)
    state = np.asarray([[128, -256, 384, -512, 640, -768, 896, -1024]], dtype=np.int16)
    instruction_id = np.asarray([7], dtype=np.uint16)
    if contract is not None:
        _validate_inputs(contract, image, state, instruction_id)
    return image, state, instruction_id
