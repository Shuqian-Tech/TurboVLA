#!/usr/bin/env python3
"""Validate the fixed-shape TurboVLA-Lite MVP contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "hardware" / "contracts" / "turbovla_lite_contract.json"


def _offsets_are_aligned(registers: dict) -> None:
    offsets = []
    for name, register in registers.items():
        offset = int(register["offset"], 16)
        width_bits = int(register["width_bits"])
        if offset % 4 or width_bits != 32:
            raise AssertionError(f"register {name} must be 32-bit and 4-byte aligned")
        offsets.append(offset)
    if len(offsets) != len(set(offsets)):
        raise AssertionError("register offsets must be unique")


def validate(contract: dict) -> None:
    assert contract["platform"] == "kr260-k26"
    assert contract["inference_location"] == "fpga_pl"
    assert contract["batch_size"] == 1
    assert contract["views"] == 1

    image = contract["image"]
    assert image["shape"] == [1, 1, 3, 128, 128]
    assert image["layout"] == "N V C H W"
    assert image["input_dtype"] == "uint8"

    language_input = contract["language"]["input"]
    assert language_input["dtype"] == "uint16"
    assert language_input["shape"] == [1]
    assert language_input["invalid_value"] == 65535

    assert contract["language"]["embedding"]["shape"] == [1, 128]
    assert contract["visual_tokens"]["shape"] == [1, 32, 128]
    assert contract["fusion"]["layers"] == 2
    assert contract["fusion"]["hidden_dim"] == 128
    assert contract["action"]["shape"] == [1, 12, 7]
    assert contract["action"]["output_dtype"] == "float32"
    assert contract["quantization"]["accumulator"] == "int32"

    for name, buffer in contract["buffers"].items():
        if buffer["alignment_bytes"] != 64:
            raise AssertionError(f"buffer {name} must be 64-byte aligned")

    _offsets_are_aligned(contract["registers"])
    version_register = contract["registers"]["contract_version"]
    assert version_register["encoding"] == "major_minor_patch_8_8_16"
    assert version_register["value"] == "0x00010000"
    assert contract["errors"]["contract_mismatch"] == 5


def main() -> int:
    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        contract = json.load(handle)
    validate(contract)
    print(f"validated {CONTRACT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
