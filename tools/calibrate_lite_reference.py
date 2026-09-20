#!/usr/bin/env python3
"""Calibrate symmetric INT8 scales for the deterministic Lite reference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.lite_reference import TurboVLALiteReference, deterministic_sample


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("build/lite/calibration.json"))
    args = parser.parse_args()

    model = TurboVLALiteReference()
    image, state, instruction_id = deterministic_sample(model.contract)
    fp32 = model.run(image, state, instruction_id, mode="fp32")
    quantization = model._require_quantization(fp32)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(quantization.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
