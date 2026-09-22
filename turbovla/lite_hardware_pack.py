"""Build the fixed-layout model and replay fixture consumed by the PL top."""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import replace
from pathlib import Path
from typing import Mapping

import numpy as np

from .lite_parameter_pack import checkpoint_parameter_arrays
from .lite_reference import (
    LiteParameters,
    LiteQuantization,
    TurboVLALiteReference,
    deterministic_sample,
    load_contract,
)

MODEL_MAGIC = 0x54564D44
CONTRACT_VERSION = 0x00030000
HEADER_BYTES = 128
MODEL_BYTES = 150656
STATE_INPUT_SCALE_OFFSET = 80
FIXTURE_STATE_INPUT_SCALE = 0.025
ACTIVATION_SCALES_OFFSET = 16
WEIGHT_SCALES_OFFSET = 48

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

TENSOR_SHAPES = {
    "conv_weight": (16, 3),
    "conv_bias": (16,),
    "visual_projection": (16, 128),
    "visual_bias": (128,),
    "instruction_table": (256, 128),
    "state_projection": (8, 128),
    "state_bias": (128,),
    "action_input": (128, 64),
    "action_input_bias": (64,),
    "action_output": (64, 84),
    "action_output_bias": (84,),
    "fusion_visual_0": (128, 128),
    "fusion_language_0": (128, 128),
    "fusion_gate_0": (128, 128),
    "fusion_bias_0": (128,),
    "fusion_visual_1": (128, 128),
    "fusion_language_1": (128, 128),
    "fusion_gate_1": (128, 128),
    "fusion_bias_1": (128,),
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


def _hardware_quantization(quantization: LiteQuantization) -> LiteQuantization:
    """Round every model-header scale to the FP32 value consumed by PL."""

    return LiteQuantization(
        activations={name: float(np.float32(value)) for name, value in quantization.activations.items()},
        weights={name: float(np.float32(value)) for name, value in quantization.weights.items()},
        state_normalization=float(np.float32(quantization.state_normalization)),
        state_input=float(np.float32(quantization.state_input)),
    )


def _quantize(value: np.ndarray, scale: float) -> np.ndarray:
    return np.clip(np.rint(value / scale), -128, 127).astype(np.int8)


def _read_header_scales(
    blob: bytes,
    manifest: Mapping[str, object],
    field: str,
    names: tuple[str, ...],
    offset: int,
) -> dict[str, float]:
    encoded = struct.unpack_from(f"<{len(names)}f", blob, offset)
    manifest_values = manifest[field]
    if not isinstance(manifest_values, Mapping):
        raise ValueError(f"manifest {field} must be a mapping")
    scales: dict[str, float] = {}
    for name, header_scale in zip(names, encoded, strict=True):
        manifest_scale = float(np.float32(manifest_values[name]))
        if not np.isfinite(header_scale) or header_scale <= 0.0 or header_scale != manifest_scale:
            raise ValueError(f"model header {field}.{name} does not match the manifest")
        scales[name] = header_scale
    return scales


def _write_tensor(blob: bytearray, name: str, value: np.ndarray) -> dict:
    if tuple(value.shape) != TENSOR_SHAPES[name]:
        raise ValueError(f"tensor {name} must have shape {TENSOR_SHAPES[name]}, got {value.shape}")
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


def _checkpoint_parameters(checkpoint: Mapping[str, object]) -> LiteParameters:
    arrays = checkpoint_parameter_arrays(checkpoint)
    return LiteParameters(
        conv_weight=arrays["conv_weight"],
        conv_bias=arrays["conv_bias"],
        visual_projection=arrays["visual_projection"],
        visual_bias=arrays["visual_bias"],
        instruction_table=arrays["instruction_table"],
        fusion_visual=np.stack([arrays[f"fusion_visual_{layer}"] for layer in range(2)]),
        fusion_language=np.stack([arrays[f"fusion_language_{layer}"] for layer in range(2)]),
        fusion_gate=np.stack([arrays[f"fusion_gate_{layer}"] for layer in range(2)]),
        fusion_bias=np.stack([arrays[f"fusion_bias_{layer}"] for layer in range(2)]),
        state_projection=arrays["state_projection"],
        state_bias=arrays["state_bias"],
        action_input=arrays["action_input"],
        action_input_bias=arrays["action_input_bias"],
        action_output=arrays["action_output"],
        action_output_bias=arrays["action_output_bias"],
    )


def _checkpoint_quantization(checkpoint: Mapping[str, object]) -> LiteQuantization:
    payload = checkpoint.get("quantization")
    if not isinstance(payload, Mapping):
        raise ValueError("checkpoint must contain QAT quantization metadata")
    activations = payload.get("activations")
    weights = payload.get("weights")
    if not isinstance(activations, Mapping) or not isinstance(weights, Mapping):
        raise ValueError("checkpoint quantization must contain activation and weight scales")
    missing_activations = set(ACTIVATION_NAMES).difference(activations)
    missing_weights = set(WEIGHT_NAMES).difference(weights)
    if missing_activations or missing_weights:
        raise ValueError(
            "checkpoint quantization is incomplete: "
            f"activations={sorted(missing_activations)}, weights={sorted(missing_weights)}"
        )
    quantization = LiteQuantization(
        activations={name: float(activations[name]) for name in ACTIVATION_NAMES},
        weights={name: float(weights[name]) for name in WEIGHT_NAMES},
        state_normalization=float(payload.get("state_normalization", 1.0 / 1024.0)),
        state_input=float(payload["state_input"]),
    )
    scales = [
        *quantization.activations.values(),
        *quantization.weights.values(),
        quantization.state_normalization,
        quantization.state_input,
    ]
    if any(not np.isfinite(scale) or scale <= 0.0 for scale in scales):
        raise ValueError("all checkpoint quantization scales must be finite and positive")
    return _hardware_quantization(quantization)


def _validate_checkpoint_contract(checkpoint: Mapping[str, object]) -> None:
    config = checkpoint.get("config")
    if not isinstance(config, Mapping):
        raise ValueError("checkpoint must contain a config mapping")
    expected = {
        "contract_version": "0.2.0",
        "hidden_dim": 128,
        "visual_tokens": 32,
        "conv_channels": 16,
        "action_hidden": 64,
        "instruction_table_size": 256,
        "state_dim": 8,
        "action_horizon": 12,
        "action_dim": 7,
        "visual_encoder": "pointwise",
    }
    for name, value in expected.items():
        actual = config.get(name, "pointwise" if name == "visual_encoder" else None)
        if actual != value:
            raise ValueError(f"checkpoint config {name}={actual!r} does not match PL value {value!r}")
    if float(config.get("state_normalization", 1.0 / 1024.0)) != 1.0 / 1024.0:
        raise ValueError("checkpoint state_normalization does not match the PL contract")


def _build_model_blob(parameters: LiteParameters, quantization: LiteQuantization) -> tuple[bytes, list[dict]]:
    blob = bytearray(MODEL_BYTES)
    struct.pack_into("<III", blob, 0, MODEL_MAGIC, CONTRACT_VERSION, MODEL_BYTES)
    activation_scales = [quantization.activations[name] for name in ACTIVATION_NAMES]
    weight_scales = [quantization.weights[name] for name in WEIGHT_NAMES]
    struct.pack_into("<8f", blob, 16, *activation_scales)
    struct.pack_into("<8f", blob, 48, *weight_scales)
    struct.pack_into("<f", blob, STATE_INPUT_SCALE_OFFSET, quantization.state_input)

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
    tensor_scales = {
        "conv_weight": weight_scales[0],
        "visual_projection": weight_scales[1],
        "instruction_table": quantization.activations["language_embedding"],
        "state_projection": weight_scales[5],
        "action_input": weight_scales[6],
        "action_output": weight_scales[7],
        **{f"fusion_visual_{layer}": weight_scales[2] for layer in range(2)},
        **{f"fusion_language_{layer}": weight_scales[3] for layer in range(2)},
        **{f"fusion_gate_{layer}": weight_scales[4] for layer in range(2)},
    }
    for tensor in tensors:
        tensor["scale"] = tensor_scales.get(tensor["name"])
    return bytes(blob), tensors


def _write_pack(output_dir: Path, files: Mapping[str, bytes], manifest: dict) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        (output_dir / name).write_bytes(payload)
    manifest["files"] = {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()}
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def export_hardware_fixture(output_dir: Path) -> dict:
    """Export one deterministic model and its exact image-to-action vector."""

    contract = load_contract()
    parameters = LiteParameters.deterministic(contract)
    reference = TurboVLALiteReference(contract=contract, parameters=parameters)
    image, state, instruction_id = deterministic_sample(contract)
    reference.run(image, state, instruction_id, mode="int8")
    quantization = reference.quantization
    assert quantization is not None
    quantization = _hardware_quantization(replace(quantization, state_input=FIXTURE_STATE_INPUT_SCALE))
    reference.quantization = quantization
    action = reference.run(image, state, instruction_id, mode="int8")["action"]

    activation_scales = [quantization.activations[name] for name in ACTIVATION_NAMES]
    weight_scales = [quantization.weights[name] for name in WEIGHT_NAMES]
    blob, tensors = _build_model_blob(parameters, quantization)
    files = {
        "model.bin": blob,
        "image.bin": image.tobytes(),
        "state.bin": state.astype("<i2").tobytes(),
        "instruction_id.bin": instruction_id.astype("<u2").tobytes(),
        "action.bin": action.astype("<f4").tobytes(),
    }
    manifest = {
        "pack_version": "1.0.0",
        "contract_version": "0.3.0",
        "contract_version_encoded": CONTRACT_VERSION,
        "model_magic": MODEL_MAGIC,
        "model_bytes": MODEL_BYTES,
        "endianness": "little",
        "zero_point": 0,
        "parameter_seed": 20260919,
        "instruction_id": int(instruction_id[0]),
        "state_input_scale": quantization.state_input,
        "activation_scales": dict(zip(ACTIVATION_NAMES, activation_scales, strict=True)),
        "weight_scales": dict(zip(WEIGHT_NAMES, weight_scales, strict=True)),
        "tensors": tensors,
        "action_shape": list(action.shape),
    }
    return _write_pack(output_dir, files, manifest)


def checkpoint_hardware_reference(checkpoint: Mapping[str, object]) -> TurboVLALiteReference:
    """Build the exact integer-arithmetic reference represented by a QAT checkpoint."""

    _validate_checkpoint_contract(checkpoint)
    return TurboVLALiteReference(
        load_contract(),
        _checkpoint_parameters(checkpoint),
        _checkpoint_quantization(checkpoint),
    )


def export_hardware_checkpoint_pack(
    checkpoint: Mapping[str, object],
    output_dir: Path,
    *,
    checkpoint_sha256: str,
    image: np.ndarray,
    state: np.ndarray,
    instruction_id: np.ndarray,
    sample: Mapping[str, object],
    checkpoint_action: np.ndarray | None = None,
) -> dict:
    """Export a trained pointwise QAT checkpoint in the exact PL model layout."""

    contract = load_contract()
    reference = checkpoint_hardware_reference(checkpoint)
    parameters = reference.parameters
    quantization = reference.quantization
    assert quantization is not None
    action = reference.run(image, state, instruction_id, mode="int8")["action"]
    blob, tensors = _build_model_blob(parameters, quantization)
    files = {
        "model.bin": blob,
        "image.bin": image.tobytes(),
        "state.bin": state.astype("<i2").tobytes(),
        "instruction_id.bin": instruction_id.astype("<u2").tobytes(),
        "action.bin": action.astype("<f4").tobytes(),
    }
    manifest = {
        "pack_version": "1.0.0",
        "contract_version": contract["contract_version"],
        "contract_version_encoded": CONTRACT_VERSION,
        "model_magic": MODEL_MAGIC,
        "model_bytes": MODEL_BYTES,
        "endianness": "little",
        "zero_point": 0,
        "source": {
            "checkpoint_sha256": checkpoint_sha256,
            "dataset_revision": checkpoint.get("dataset_revision"),
            "mode": checkpoint.get("mode"),
            "seed": checkpoint.get("seed"),
        },
        "instructions": checkpoint.get("instructions"),
        "sample": dict(sample),
        "instruction_id": int(instruction_id[0]),
        "state_input_scale": quantization.state_input,
        "state_normalization": quantization.state_normalization,
        "activation_scales": dict(quantization.activations),
        "weight_scales": dict(quantization.weights),
        "tensors": tensors,
        "action_shape": list(action.shape),
    }
    if checkpoint_action is not None:
        delta = np.abs(checkpoint_action.astype(np.float32) - action)
        manifest["checkpoint_fake_quant_parity"] = {
            "max_abs_error": float(np.max(delta)),
            "mean_abs_error": float(np.mean(delta)),
        }
    return _write_pack(output_dir, files, manifest)


def load_hardware_reference(pack_dir: Path) -> TurboVLALiteReference:
    """Validate a PL model pack and reconstruct its exact INT8 reference."""

    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    blob = (pack_dir / "model.bin").read_bytes()
    if hashlib.sha256(blob).hexdigest() != manifest["files"]["model.bin"]:
        raise ValueError("model.bin checksum does not match manifest")
    if len(blob) != MODEL_BYTES:
        raise ValueError(f"model.bin must contain {MODEL_BYTES} bytes")
    magic, version, total_bytes = struct.unpack_from("<III", blob, 0)
    if (magic, version, total_bytes) != (MODEL_MAGIC, CONTRACT_VERSION, MODEL_BYTES):
        raise ValueError("model.bin header does not match the Lite PL contract")

    entries = {entry["name"]: entry for entry in manifest["tensors"]}
    if len(entries) != len(TENSOR_SHAPES) or set(entries) != set(TENSOR_SHAPES):
        raise ValueError("manifest tensors do not match the fixed Lite PL layout")
    arrays: dict[str, np.ndarray] = {}
    for name, shape in TENSOR_SHAPES.items():
        entry = entries[name]
        dtype_name = "float32" if "bias" in name else "int8"
        dtype = {"int8": np.dtype("<i1"), "float32": np.dtype("<f4")}[dtype_name]
        expected_nbytes = int(np.prod(shape)) * dtype.itemsize
        expected_layout = {
            "dtype": dtype_name,
            "nbytes": expected_nbytes,
            "offset": HEADER_BYTES + TENSOR_OFFSETS[name],
            "shape": list(shape),
        }
        if any(entry[field] != value for field, value in expected_layout.items()):
            raise ValueError(f"manifest tensor {name} does not match the fixed Lite PL layout")
        payload = blob[entry["offset"] : entry["offset"] + entry["nbytes"]]
        if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError(f"model tensor {name} checksum does not match manifest")
        arrays[name] = np.frombuffer(payload, dtype=dtype).reshape(shape)

    activation_scales = _read_header_scales(
        blob, manifest, "activation_scales", ACTIVATION_NAMES, ACTIVATION_SCALES_OFFSET
    )
    weight_scales = _read_header_scales(blob, manifest, "weight_scales", WEIGHT_NAMES, WEIGHT_SCALES_OFFSET)
    header_state_scale = struct.unpack_from("<f", blob, STATE_INPUT_SCALE_OFFSET)[0]
    if (
        not np.isfinite(header_state_scale)
        or header_state_scale <= 0.0
        or header_state_scale != float(np.float32(manifest["state_input_scale"]))
    ):
        raise ValueError("model header state_input scale does not match the manifest")
    quantization = LiteQuantization(
        activation_scales,
        weight_scales,
        float(manifest.get("state_normalization", 1.0 / 1024.0)),
        header_state_scale,
    )

    def weight(name: str, scale: float) -> np.ndarray:
        return arrays[name].astype(np.float32) * np.float32(scale)

    parameters = LiteParameters(
        conv_weight=weight("conv_weight", weight_scales["conv_weight"]),
        conv_bias=arrays["conv_bias"].astype(np.float32),
        visual_projection=weight("visual_projection", weight_scales["visual_projection"]),
        visual_bias=arrays["visual_bias"].astype(np.float32),
        instruction_table=weight("instruction_table", activation_scales["language_embedding"]),
        fusion_visual=np.stack(
            [weight(f"fusion_visual_{layer}", weight_scales["fusion_visual"]) for layer in range(2)]
        ),
        fusion_language=np.stack(
            [weight(f"fusion_language_{layer}", weight_scales["fusion_language"]) for layer in range(2)]
        ),
        fusion_gate=np.stack(
            [weight(f"fusion_gate_{layer}", weight_scales["fusion_gate"]) for layer in range(2)]
        ),
        fusion_bias=np.stack([arrays[f"fusion_bias_{layer}"].astype(np.float32) for layer in range(2)]),
        state_projection=weight("state_projection", weight_scales["state_projection"]),
        state_bias=arrays["state_bias"].astype(np.float32),
        action_input=weight("action_input", weight_scales["action_input"]),
        action_input_bias=arrays["action_input_bias"].astype(np.float32),
        action_output=weight("action_output", weight_scales["action_output"]),
        action_output_bias=arrays["action_output_bias"].astype(np.float32),
    )
    return TurboVLALiteReference(load_contract(), parameters, quantization)
