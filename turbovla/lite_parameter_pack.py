"""Export and load aligned INT8/FP32 TurboVLA-Lite parameter packs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np

from .lite_reference import LiteParameters, load_contract

ALIGNMENT = 64
PACK_VERSION = "0.1.0"


@dataclass(frozen=True)
class PackedTensor:
    name: str
    dtype: str
    shape: tuple[int, ...]
    offset: int
    nbytes: int
    scale: float | None
    checksum: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "shape": list(self.shape),
            "offset": self.offset,
            "nbytes": self.nbytes,
            "scale": self.scale,
            "checksum": self.checksum,
        }


def _aligned_offset(offset: int) -> int:
    return (offset + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT


def _quantize_weight(value: np.ndarray) -> tuple[np.ndarray, float]:
    maximum = float(np.max(np.abs(value)))
    scale = max(maximum / 127.0, 1.0e-8)
    return np.clip(np.rint(value / scale), -128, 127).astype(np.int8), scale


def _checkpoint_arrays(checkpoint: Mapping[str, object]) -> dict[str, np.ndarray]:
    config = checkpoint.get("config")
    if isinstance(config, Mapping) and config.get("visual_encoder", "pointwise") != "pointwise":
        raise ValueError("experimental visual encoders cannot be exported with the current FPGA contract")
    state_dict = checkpoint.get("state_dict")
    if not isinstance(state_dict, Mapping):
        raise ValueError("checkpoint must contain a state_dict mapping")
    if any(name.startswith(("spatial_depthwise.", "spatial_pointwise.")) for name in state_dict):
        raise ValueError("experimental visual encoder weights cannot be exported with the current FPGA contract")

    def array(name: str) -> np.ndarray:
        value = state_dict[name]
        return value.detach().cpu().numpy().astype(np.float32, copy=False)

    arrays = {
        "conv_weight": array("conv.weight").reshape(16, 3),
        "conv_bias": array("conv.bias"),
        "visual_projection": array("visual_projection.weight").T,
        "visual_bias": array("visual_projection.bias"),
        "instruction_table": array("instruction_embedding.weight"),
        "state_projection": array("state_projection.weight").T,
        "state_bias": array("state_projection.bias"),
        "action_input": array("action_input.weight").T,
        "action_input_bias": array("action_input.bias"),
        "action_output": array("action_output.weight").T,
        "action_output_bias": array("action_output.bias"),
    }
    for layer in range(2):
        arrays[f"fusion_visual_{layer}"] = array(f"fusion_visual.{layer}.weight").T
        arrays[f"fusion_language_{layer}"] = array(f"fusion_language.{layer}.weight").T
        arrays[f"fusion_gate_{layer}"] = array(f"fusion_gate.{layer}.weight").T
        arrays[f"fusion_bias_{layer}"] = array(f"fusion_visual.{layer}.bias")
    return arrays


def _parameter_arrays(parameters: LiteParameters) -> dict[str, np.ndarray]:
    arrays = parameters.arrays()
    return {
        "conv_weight": arrays["conv_weight"],
        "conv_bias": arrays["conv_bias"],
        "visual_projection": arrays["visual_projection"],
        "visual_bias": arrays["visual_bias"],
        "instruction_table": arrays["instruction_table"],
        "state_projection": arrays["state_projection"],
        "state_bias": arrays["state_bias"],
        "action_input": arrays["action_input"],
        "action_input_bias": arrays["action_input_bias"],
        "action_output": arrays["action_output"],
        "action_output_bias": arrays["action_output_bias"],
        **{f"fusion_visual_{layer}": arrays["fusion_visual"][layer] for layer in range(2)},
        **{f"fusion_language_{layer}": arrays["fusion_language"][layer] for layer in range(2)},
        **{f"fusion_gate_{layer}": arrays["fusion_gate"][layer] for layer in range(2)},
        **{f"fusion_bias_{layer}": arrays["fusion_bias"][layer] for layer in range(2)},
    }


def export_parameter_pack(
    parameters: LiteParameters | None,
    output_dir: Path,
    contract: Mapping | None = None,
    checkpoint: Mapping[str, object] | None = None,
) -> dict:
    """Write aligned binary tensors and a self-describing manifest."""

    if (parameters is None) == (checkpoint is None):
        raise ValueError("provide exactly one of parameters or checkpoint")
    arrays = _parameter_arrays(parameters) if parameters is not None else _checkpoint_arrays(checkpoint or {})
    contract = contract or load_contract()
    output_dir.mkdir(parents=True, exist_ok=True)
    binary = bytearray()
    manifest_tensors: list[PackedTensor] = []
    for name, value in arrays.items():
        if value.dtype.kind not in "fi":
            raise ValueError(f"unsupported parameter dtype for {name}: {value.dtype}")
        if value.dtype.kind == "f" and "bias" not in name:
            encoded, scale = _quantize_weight(value)
            dtype = "int8"
        else:
            encoded = np.asarray(value, dtype=np.float32)
            scale = None
            dtype = "float32"
        encoded = np.ascontiguousarray(encoded)
        offset = _aligned_offset(len(binary))
        binary.extend(b"\0" * (offset - len(binary)))
        payload = encoded.tobytes(order="C")
        binary.extend(payload)
        manifest_tensors.append(
            PackedTensor(
                name=name,
                dtype=dtype,
                shape=tuple(encoded.shape),
                offset=offset,
                nbytes=len(payload),
                scale=scale,
                checksum=hashlib.sha256(payload).hexdigest(),
            )
        )
    weights_path = output_dir / "weights.bin"
    weights_path.write_bytes(binary)
    manifest = {
        "pack_version": PACK_VERSION,
        "contract_version": contract["contract_version"],
        "platform": contract["platform"],
        "endianness": "little",
        "alignment_bytes": ALIGNMENT,
        "weights_file": weights_path.name,
        "weights_sha256": hashlib.sha256(binary).hexdigest(),
        "tensors": [tensor.to_dict() for tensor in manifest_tensors],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_parameter_pack(pack_dir: Path) -> dict[str, np.ndarray]:
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    binary = (pack_dir / manifest["weights_file"]).read_bytes()
    if hashlib.sha256(binary).hexdigest() != manifest["weights_sha256"]:
        raise ValueError("weights.bin checksum does not match manifest")
    result: dict[str, np.ndarray] = {}
    dtypes = {"int8": np.dtype("<i1"), "float32": np.dtype("<f4")}
    for entry in manifest["tensors"]:
        dtype = dtypes[entry["dtype"]]
        payload = binary[entry["offset"] : entry["offset"] + entry["nbytes"]]
        if hashlib.sha256(payload).hexdigest() != entry["checksum"]:
            raise ValueError(f"checksum mismatch for tensor {entry['name']}")
        result[entry["name"]] = np.frombuffer(payload, dtype=dtype).reshape(tuple(entry["shape"]))
    return result


def reconstruct_reference_parameters(pack_dir: Path) -> LiteParameters:
    """Dequantize a pack into the T002 reference parameter structure."""

    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in manifest["tensors"]}
    packed = load_parameter_pack(pack_dir)

    def tensor(name: str) -> np.ndarray:
        value = packed[name].astype(np.float32)
        scale = entries[name]["scale"]
        return value * float(scale) if scale is not None else value

    return LiteParameters(
        conv_weight=tensor("conv_weight"),
        conv_bias=tensor("conv_bias"),
        visual_projection=tensor("visual_projection"),
        visual_bias=tensor("visual_bias"),
        instruction_table=tensor("instruction_table"),
        fusion_visual=np.stack([tensor(f"fusion_visual_{layer}") for layer in range(2)]),
        fusion_language=np.stack([tensor(f"fusion_language_{layer}") for layer in range(2)]),
        fusion_gate=np.stack([tensor(f"fusion_gate_{layer}") for layer in range(2)]),
        fusion_bias=np.stack([tensor(f"fusion_bias_{layer}") for layer in range(2)]),
        state_projection=tensor("state_projection"),
        state_bias=tensor("state_bias"),
        action_input=tensor("action_input"),
        action_input_bias=tensor("action_input_bias"),
        action_output=tensor("action_output"),
        action_output_bias=tensor("action_output_bias"),
    )
