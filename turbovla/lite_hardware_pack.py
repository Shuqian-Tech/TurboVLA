"""Build the fixed-layout model and replay fixture consumed by the PL top."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import numpy as np

from .lite_reference import LiteParameters, TurboVLALiteReference, deterministic_sample, load_contract

MODEL_MAGIC = 0x54564D44
CONTRACT_VERSION = 0x00020000
HEADER_BYTES = 128
MODEL_BYTES = 150656

TENSOR_OFFSETS = {
    "conv_weight": 0,
    "conv_bias": 64,
    "visual_projection": 128,
    "visual_bias": 2176,
    "instruction_table": 2688,
    "state_projection": 35456,
    "state_bias": 36480,
    "action_input": 36992,
    "action_input_bias": 45184,
    "action_output": 45440,
    "action_output_bias": 50816,
    "fusion_visual_0": 51200,
    "fusion_language_0": 67584,
    "fusion_gate_0": 83968,
    "fusion_bias_0": 100352,
    "fusion_visual_1": 100864,
    "fusion_language_1": 117248,
    "fusion_gate_1": 133632,
    "fusion_bias_1": 150016,
}

ACTIVATION_NAMES = (
    "image_normalized",
    "visual_conv",
    "visual_tokens",
    "language_embedding",
    "fusion_0",
    "fusion_1",
    "state_projection",
    "action_hidden",
)
WEIGHT_NAMES = (
    "conv_weight",
    "visual_projection",
    "fusion_visual",
    "fusion_language",
    "fusion_gate",
    "state_projection",
    "action_input",
    "action_output",
)


def _quantize(value: np.ndarray, scale: float) -> np.ndarray:
    return np.clip(np.rint(value / scale), -128, 127).astype(np.int8)


def _write_tensor(blob: bytearray, name: str, value: np.ndarray) -> dict:
    payload = np.ascontiguousarray(value).tobytes()
    offset = HEADER_BYTES + TENSOR_OFFSETS[name]
    blob[offset : offset + len(payload)] = payload
    return {
        "name": name,
        "offset": offset,
        "nbytes": len(payload),
        "dtype": str(value.dtype),
        "shape": list(value.shape),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def export_hardware_fixture(output_dir: Path) -> dict:
    """Export one deterministic model and its exact image-to-action vector."""

    contract = load_contract()
    parameters = LiteParameters.deterministic(contract)
    reference = TurboVLALiteReference(contract=contract, parameters=parameters)
    image, state, instruction_id = deterministic_sample(contract)
    action = reference.run(image, state, instruction_id, mode="int8")["action"]
    quantization = reference.quantization
    assert quantization is not None

    blob = bytearray(MODEL_BYTES)
    struct.pack_into("<III", blob, 0, MODEL_MAGIC, CONTRACT_VERSION, MODEL_BYTES)
    activation_scales = [quantization.activations[name] for name in ACTIVATION_NAMES]
    weight_scales = [quantization.weights[name] for name in WEIGHT_NAMES]
    struct.pack_into("<8f", blob, 16, *activation_scales)
    struct.pack_into("<8f", blob, 48, *weight_scales)

    tensors: list[dict] = []
    tensors.append(_write_tensor(blob, "conv_weight", _quantize(parameters.conv_weight, weight_scales[0])))
    tensors.append(_write_tensor(blob, "conv_bias", parameters.conv_bias.astype("<f4")))
    tensors.append(
        _write_tensor(blob, "visual_projection", _quantize(parameters.visual_projection, weight_scales[1]))
    )
    tensors.append(_write_tensor(blob, "visual_bias", parameters.visual_bias.astype("<f4")))
    tensors.append(
        _write_tensor(
            blob,
            "instruction_table",
            _quantize(parameters.instruction_table, quantization.activations["language_embedding"]),
        )
    )
    tensors.append(_write_tensor(blob, "state_projection", _quantize(parameters.state_projection, weight_scales[5])))
    tensors.append(_write_tensor(blob, "state_bias", parameters.state_bias.astype("<f4")))
    tensors.append(_write_tensor(blob, "action_input", _quantize(parameters.action_input, weight_scales[6])))
    tensors.append(_write_tensor(blob, "action_input_bias", parameters.action_input_bias.astype("<f4")))
    tensors.append(_write_tensor(blob, "action_output", _quantize(parameters.action_output, weight_scales[7])))
    tensors.append(_write_tensor(blob, "action_output_bias", parameters.action_output_bias.astype("<f4")))
    for layer in range(2):
        tensors.append(
            _write_tensor(blob, f"fusion_visual_{layer}", _quantize(parameters.fusion_visual[layer], weight_scales[2]))
        )
        tensors.append(
            _write_tensor(
                blob, f"fusion_language_{layer}", _quantize(parameters.fusion_language[layer], weight_scales[3])
            )
        )
        tensors.append(
            _write_tensor(blob, f"fusion_gate_{layer}", _quantize(parameters.fusion_gate[layer], weight_scales[4]))
        )
        tensors.append(_write_tensor(blob, f"fusion_bias_{layer}", parameters.fusion_bias[layer].astype("<f4")))

    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "model.bin": bytes(blob),
        "image.bin": image.tobytes(),
        "state.bin": state.astype("<i2").tobytes(),
        "instruction_id.bin": instruction_id.astype("<u2").tobytes(),
        "action.bin": action.astype("<f4").tobytes(),
    }
    for name, payload in files.items():
        (output_dir / name).write_bytes(payload)
    manifest = {
        "contract_version": "0.2.0",
        "contract_version_encoded": CONTRACT_VERSION,
        "model_magic": MODEL_MAGIC,
        "model_bytes": MODEL_BYTES,
        "parameter_seed": 20260919,
        "instruction_id": int(instruction_id[0]),
        "activation_scales": dict(zip(ACTIVATION_NAMES, activation_scales, strict=True)),
        "weight_scales": dict(zip(WEIGHT_NAMES, weight_scales, strict=True)),
        "tensors": tensors,
        "files": {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()},
        "action_shape": list(action.shape),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
