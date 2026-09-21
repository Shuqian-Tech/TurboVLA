#!/usr/bin/env python3
"""Run repeated software closed-loop replay with safety fault injection."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.safety import SafetyPolicy


def run_stability(action: np.ndarray, cycles: int) -> dict:
    policy = SafetyPolicy()
    accepted = 0
    first_action = None
    max_drift = 0.0
    start = time.monotonic()
    for cycle in range(cycles):
        decision = policy.apply(action, now=float(cycle) * 0.01)
        if not decision.accepted:
            raise AssertionError(f"unexpected safety rejection at cycle {cycle}: {decision.reason}")
        accepted += 1
        first_action = decision.action.copy() if first_action is None else first_action
        max_drift = max(max_drift, float(np.max(np.abs(decision.action - first_action))))

    fault_results = {}
    nan_action = action.copy()
    nan_action[0, 0, 0] = np.nan
    fault_results["non_finite_action"] = policy.apply(nan_action, now=cycles * 0.01).reason
    policy.emergency_stop = True
    fault_results["emergency_stop"] = policy.apply(action, now=cycles * 0.01).reason
    policy.emergency_stop = False
    policy.communication_connected = False
    fault_results["communication_disconnected"] = policy.apply(action, now=cycles * 0.01).reason
    policy.communication_connected = True
    policy.last_frame_time = 0.0
    fault_results["frame_timeout"] = policy.apply(action, now=1.0).reason
    return {
        "verification_mode": "software_only",
        "hardware_bringup": "not_run",
        "cycles": cycles,
        "accepted_cycles": accepted,
        "max_action_drift": max_drift,
        "elapsed_seconds": time.monotonic() - start,
        "fault_results": fault_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", type=Path, default=Path("tests/data/lite_golden/golden_tensors.npz"))
    parser.add_argument("--output", type=Path, default=Path("tests/data/lite_stability_report.json"))
    parser.add_argument("--cycles", type=int, default=1000)
    args = parser.parse_args()
    if args.cycles < 1:
        raise SystemExit("--cycles must be positive")
    with np.load(args.action) as bundle:
        action = np.asarray(bundle["fp32_action"], dtype=np.float32)
    report = run_stability(action, args.cycles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

