#!/usr/bin/env python3
"""Compare two golden NPZ files by tensor name and report absolute errors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    reference = np.load(args.reference)
    candidate = np.load(args.candidate)
    reference_names = {name for name in reference.files if name.startswith("fp32_")}
    candidate_names = {name for name in candidate.files if name.startswith("fp32_")}
    if reference_names != candidate_names:
        missing = sorted(reference_names - candidate_names)
        extra = sorted(candidate_names - reference_names)
        raise SystemExit(f"tensor names differ: missing={missing}, extra={extra}")
    report = {}
    for name in sorted(reference_names):
        expected = reference[name]
        actual = candidate[name]
        if expected.shape != actual.shape:
            raise SystemExit(f"shape differs for {name}: {expected.shape} != {actual.shape}")
        delta = np.abs(expected.astype(np.float32) - actual.astype(np.float32))
        report[name] = {"max_abs_error": float(delta.max()), "mean_abs_error": float(delta.mean())}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

