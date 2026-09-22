from __future__ import annotations

import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from turbovla.lite_hardware_pack import (
    ACTIVATION_NAMES,
    CONTRACT_VERSION,
    FIXTURE_STATE_INPUT_SCALE,
    HEADER_BYTES,
    MODEL_BYTES,
    STATE_INPUT_SCALE_OFFSET,
    TENSOR_OFFSETS,
    WEIGHT_NAMES,
    export_hardware_checkpoint_pack,
    export_hardware_fixture,
    load_hardware_reference,
)
from turbovla.lite_reference import deterministic_sample, load_contract
from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "data" / "lite_hardware_e2e"
FORMAL_PACK = ROOT / "tests" / "data" / "lite_parameter_pack_qat"
FORMAL_CHECKPOINT_SHA256 = "7209a40065aa72628bd1a2b3b92d92a205ac97a4bb1a4577c1e4eda3d5d5dc1a"


class LiteHardwarePackTest(unittest.TestCase):
    def test_checked_fixture_is_reproducible(self) -> None:
        expected = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            actual = export_hardware_fixture(Path(directory))
        self.assertEqual(actual["files"], expected["files"])
        self.assertEqual(actual["tensors"], expected["tensors"])
        self.assertEqual(actual["contract_version"], "0.3.0")

    def test_model_checksum_matches_manifest(self) -> None:
        manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
        model = (FIXTURE / "model.bin").read_bytes()
        digest = hashlib.sha256(model).hexdigest()
        self.assertEqual(digest, manifest["files"]["model.bin"])
        encoded_scale = struct.unpack_from("<f", model, STATE_INPUT_SCALE_OFFSET)[0]
        self.assertAlmostEqual(encoded_scale, FIXTURE_STATE_INPUT_SCALE)
        self.assertEqual(manifest["state_input_scale"], encoded_scale)

    def test_trained_checkpoint_round_trip_preserves_exact_int8_output(self) -> None:
        state_input_scale = 0.025436761811023622
        quantization = {
            "activations": {name: 0.02 for name in (*ACTIVATION_NAMES, "action")},
            "weights": {name: 0.01 for name in (*WEIGHT_NAMES, "instruction_table")},
            "state_input": state_input_scale,
            "state_normalization": 1.0 / 1024.0,
        }
        config = LiteStudentConfig.from_contract(load_contract())
        model = TurboVLALiteStudent(config, quantization)
        checkpoint = {
            "config": config.to_dict(),
            "state_dict": model.state_dict(),
            "quantization": quantization,
            "mode": "qat",
            "seed": 7,
        }
        image, state, instruction_id = deterministic_sample(load_contract())
        state[0, 0] = 3308
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            manifest = export_hardware_checkpoint_pack(
                checkpoint,
                output,
                checkpoint_sha256="0" * 64,
                image=image,
                state=state,
                instruction_id=instruction_id,
                sample={"index": 0},
            )
            loaded = load_hardware_reference(output)
            actual = loaded.run(image, state, instruction_id, mode="int8")["action"]
            expected = np.fromfile(output / "action.bin", dtype="<f4").reshape(1, 12, 7)
            np.testing.assert_array_equal(actual, expected)
            encoded = struct.unpack_from("<f", (output / "model.bin").read_bytes(), STATE_INPUT_SCALE_OFFSET)[0]
            self.assertEqual(encoded, manifest["state_input_scale"])
            self.assertEqual(manifest["source"]["mode"], "qat")

    def test_formal_qat_pack_uses_v03_header_and_frozen_layout(self) -> None:
        manifest = json.loads((FORMAL_PACK / "manifest.json").read_text(encoding="utf-8"))
        model = (FORMAL_PACK / "model.bin").read_bytes()
        self.assertEqual(len(model), MODEL_BYTES)
        self.assertEqual(struct.unpack_from("<I", model, 4)[0], CONTRACT_VERSION)
        self.assertEqual(
            struct.unpack_from("<f", model, STATE_INPUT_SCALE_OFFSET)[0],
            manifest["state_input_scale"],
        )
        self.assertEqual(manifest["source"]["checkpoint_sha256"], FORMAL_CHECKPOINT_SHA256)
        self.assertEqual(manifest["files"]["model.bin"], hashlib.sha256(model).hexdigest())
        self.assertEqual(len(manifest["tensors"]), 19)
        self.assertEqual(
            {entry["name"]: entry["offset"] for entry in manifest["tensors"]},
            {name: HEADER_BYTES + offset for name, offset in TENSOR_OFFSETS.items()},
        )

        image = np.fromfile(FORMAL_PACK / "image.bin", dtype=np.uint8).reshape(1, 1, 3, 128, 128)
        state = np.fromfile(FORMAL_PACK / "state.bin", dtype="<i2").reshape(1, 8)
        instruction_id = np.fromfile(FORMAL_PACK / "instruction_id.bin", dtype="<u2")
        expected = np.fromfile(FORMAL_PACK / "action.bin", dtype="<f4").reshape(1, 12, 7)
        actual = load_hardware_reference(FORMAL_PACK).run(image, state, instruction_id, mode="int8")["action"]
        np.testing.assert_array_equal(actual, expected)


if __name__ == "__main__":
    unittest.main()
