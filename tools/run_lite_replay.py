#!/usr/bin/env python3
"""Replay the fixed T002 golden bundle and emit layer/action error metrics."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.lite_reference import TurboVLALiteReference


def _percentile(values: list[float], percentile: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), percentile))


def replay_bundle(bundle_path: Path, repeats: int = 20) -> dict:
    with np.load(bundle_path) as bundle:
        image = np.asarray(bundle["image"])
        state = np.asarray(bundle["state"])
        instruction_id = np.asarray(bundle["instruction_id"])
        expected = {name: np.asarray(bundle[name]) for name in bundle.files if name.startswith("fp32_")}
        expected_int8 = {name: np.asarray(bundle[name]) for name in bundle.files if name.startswith("int8_")}
    model = TurboVLALiteReference()
    metrics: dict[str, dict[str, float]] = {}
    timings: dict[str, dict[str, float]] = {}
    for mode, expected_values in (("fp32", expected), ("int8", expected_int8)):
        for _ in range(2):
            model.run(image, state, instruction_id, mode=mode)
        elapsed = []
        actual = None
        for _ in range(repeats):
            start = time.perf_counter()
            actual = model.run(image, state, instruction_id, mode=mode)
            elapsed.append((time.perf_counter() - start) * 1000.0)
        timings[mode] = {"p50_ms": _percentile(elapsed, 50), "p99_ms": _percentile(elapsed, 99)}
        assert actual is not None
        for name, expected_tensor in expected_values.items():
            tensor_name = name.split("_", 1)[1]
            if tensor_name not in actual or actual[tensor_name].shape != expected_tensor.shape:
                raise AssertionError(f"replay shape mismatch for {mode}:{tensor_name}")
            delta = np.abs(actual[tensor_name].astype(np.float32) - expected_tensor.astype(np.float32))
            metrics[f"{mode}:{tensor_name}"] = {
                "max_abs_error": float(delta.max()),
                "mean_abs_error": float(delta.mean()),
            }
    action = metrics["int8:action"]
    return {
        "verification_mode": "software_only",
        "hardware_bringup": "not_run",
        "bundle": str(bundle_path),
        "sample_count": int(image.shape[0]),
        "layers": metrics,
        "action_error": action,
        "latency_ms": timings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, default=Path("tests/data/lite_golden/golden_tensors.npz"))
    parser.add_argument("--output", type=Path, default=Path("tests/data/lite_replay_report.json"))
    parser.add_argument("--repeats", type=int, default=20)
    args = parser.parse_args()
    if args.repeats < 2:
        raise SystemExit("--repeats must be at least 2")
    report = replay_bundle(args.bundle, repeats=args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
