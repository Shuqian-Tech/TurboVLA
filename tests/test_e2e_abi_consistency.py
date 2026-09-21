from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from turbovla.lite_hardware_pack import HEADER_BYTES, MODEL_BYTES, TENSOR_OFFSETS

ROOT = Path(__file__).resolve().parents[1]


def _constant(path: Path, name: str) -> int:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"constexpr (?:std::size_t|std::uint32_t) {name} = (0x[0-9A-Fa-f]+|[0-9]+)(?:U)?;", text)
    if match is None:
        raise AssertionError(f"missing direct constant {name} in {path}")
    return int(match.group(1), 0)


class E2eAbiConsistencyTest(unittest.TestCase):
    def test_arena_layout_matches_contract_and_runtime(self) -> None:
        contract = json.loads((ROOT / "hardware/contracts/turbovla_lite_contract.json").read_text())
        hls = ROOT / "hardware/hls/e2e/e2e.h"
        runtime = ROOT / "runtime/include/turbovla_runtime.hpp"
        names = {
            "image": "kImageOffset",
            "state": "kStateOffset",
            "model": "kModelOffset",
            "action": "kActionOffset",
        }
        for segment, constant in names.items():
            expected = contract["buffers"][segment]["offset"]
            self.assertEqual(_constant(hls, constant), expected)
            self.assertEqual(_constant(runtime, constant), expected)
        self.assertEqual(_constant(hls, "kArenaBytes"), contract["buffers"]["arena"]["size_bytes"])
        self.assertEqual(_constant(runtime, "kArenaBytes"), contract["buffers"]["arena"]["size_bytes"])

    def test_register_offsets_match_generated_hls_shape(self) -> None:
        register_map = json.loads((ROOT / "hardware/vivado_kr260/register_map.json").read_text())
        runtime = ROOT / "runtime/include/turbovla_runtime.hpp"
        names = {
            "control": "kControlOffset",
            "global_interrupt_enable": "kGlobalInterruptOffset",
            "interrupt_enable": "kInterruptEnableOffset",
            "interrupt_status": "kInterruptStatusOffset",
            "kernel_return": "kKernelReturnOffset",
            "arena_addr_lo": "kArenaAddressLowOffset",
            "arena_addr_hi": "kArenaAddressHighOffset",
        }
        for register, constant in names.items():
            self.assertEqual(_constant(runtime, constant), int(register_map["registers"][register]["offset"], 16))

    def test_model_tensor_offsets_match_hls_header(self) -> None:
        header = (ROOT / "hardware/hls/e2e/model_layout.h").read_text(encoding="utf-8")
        self.assertEqual(MODEL_BYTES, 150656)
        for tensor, offset in TENSOR_OFFSETS.items():
            cpp_name = "k" + "".join(part.title() for part in tensor.split("_"))
            match = re.search(rf"constexpr std::size_t {cpp_name} = kTensorBase \+ ([0-9]+);", header)
            self.assertIsNotNone(match, cpp_name)
            self.assertEqual(HEADER_BYTES + offset, HEADER_BYTES + int(match.group(1)))


if __name__ == "__main__":
    unittest.main()
