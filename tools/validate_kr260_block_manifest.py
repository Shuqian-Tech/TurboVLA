#!/usr/bin/env python3
"""Validate the static KR260 block-design contract without Vivado."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "hardware" / "contracts" / "turbovla_lite_contract.json"
REGISTER_MAP = ROOT / "hardware" / "vivado_kr260" / "register_map.json"


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    register_map = json.loads(REGISTER_MAP.read_text(encoding="utf-8"))
    if register_map["platform"] != "kr260-k26" or contract["platform"] != register_map["platform"]:
        raise AssertionError("only KR260/K26 is supported")
    if register_map["contract_version"] != contract["contract_version"]:
        raise AssertionError("register map contract version mismatch")
    expected = contract["registers"]
    actual = register_map["registers"]
    if set(expected) != set(actual):
        raise AssertionError("register names differ from hardware contract")
    offsets = []
    for name, entry in actual.items():
        offset = int(entry["offset"], 16)
        if offset % 4:
            raise AssertionError(f"register {name} is not 4-byte aligned")
        offsets.append(offset)
        if offset != int(expected[name]["offset"], 16):
            raise AssertionError(f"register {name} offset differs from contract")
    if len(offsets) != len(set(offsets)):
        raise AssertionError("register offsets are not unique")
    for name, buffer in register_map["buffers"].items():
        if buffer["alignment_bytes"] != 64:
            raise AssertionError(f"buffer {name} is not 64-byte aligned")
    if register_map["control_protocol"] != "ap_ctrl_hs":
        raise AssertionError("runtime must use the HLS ap_ctrl_hs protocol")
    if register_map["buffers"]["arena"]["size_bytes"] != 200320:
        raise AssertionError("runtime arena size mismatch")
    print(f"validated KR260 block manifest with {len(actual)} registers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
