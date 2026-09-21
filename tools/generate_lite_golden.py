#!/usr/bin/env python3
"""Generate deterministic inputs, FP32/INT8 tensors, and error metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.lite_reference import TurboVLALiteReference, deterministic_sample


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("build/lite/golden"))
    args = parser.parse_args()

    model = TurboVLALiteReference()
    image, state, instruction_id = deterministic_sample(model.contract)
    fp32 = model.run(image, state, instruction_id, mode="fp32")
    int8 = model.run(image, state, instruction_id, mode="int8")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output_dir / "golden_tensors.npz",
        image=image,
        state=state,
        instruction_id=instruction_id,
        **{f"fp32_{name}": value for name, value in fp32.items()},
        **{f"int8_{name}": value for name, value in int8.items()},
    )
    (args.output_dir / "calibration.json").write_text(
        json.dumps(model.quantization.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "comparison.json").write_text(
        json.dumps(model.compare(image, state, instruction_id), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    metadata = {
        "contract_version": model.contract["contract_version"],
        "parameter_seed": 20260919,
        "tensor_names": sorted(fp32),
        "input_shapes": {
            "image": list(image.shape),
            "state": list(state.shape),
            "instruction_id": list(instruction_id.shape),
        },
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.output_dir / 'golden_tensors.npz'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
