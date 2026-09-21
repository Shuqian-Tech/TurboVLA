#!/usr/bin/env python3
"""Aggregate fixed-split TurboVLA-Lite GPU evaluation reports."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "population_std": statistics.pstdev(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.report) < 2:
        parser.error("at least two --report inputs are required")

    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.report]
    split_seeds = {report.get("split_seed") for report in reports}
    revisions = {report.get("dataset_revision") for report in reports}
    validation_counts = {report["validation_samples_used"] for report in reports}
    modes = {report["mode"] for report in reports}
    if len(split_seeds) != 1 or None in split_seeds:
        raise ValueError(f"reports do not share an explicit split seed: {split_seeds}")
    if len(revisions) != 1 or len(validation_counts) != 1 or len(modes) != 1:
        raise ValueError("reports must share dataset revision, validation sample count, and mode")

    final = [report["curve"][-1]["validation"] for report in reports]
    tasks = set(final[0]["per_task_action_mae"])
    if any(set(item["per_task_action_mae"]) != tasks for item in final[1:]):
        raise ValueError("reports do not cover the same task set")
    dimension_count = len(final[0]["action_dimension_mae"])
    if any(len(item["action_dimension_mae"]) != dimension_count for item in final[1:]):
        raise ValueError("reports do not share the same action dimension")

    payload = {
        "schema_version": "1.0.0",
        "scope": "offline_libero_spatial_demonstration_validation",
        "decision_status": "preliminary_tune",
        "deployment_claim": "none",
        "mode": reports[0]["mode"],
        "dataset_revision": reports[0]["dataset_revision"],
        "split_seed": reports[0]["split_seed"],
        "validation_samples": reports[0]["validation_samples_used"],
        "seeds": [report["seed"] for report in reports],
        "action_mae": _summary([item["action_mae"] for item in final]),
        "gripper_sign_accuracy": _summary([item["gripper_sign_accuracy"] for item in final]),
        "action_dimension_mae": [
            _summary([item["action_dimension_mae"][dimension] for item in final])
            for dimension in range(dimension_count)
        ],
        "per_task_action_mae": {
            task: _summary([item["per_task_action_mae"][task] for item in final]) for task in sorted(tasks)
        },
        "runs": [
            {
                "report": str(path),
                "seed": report["seed"],
                "checkpoint": report["checkpoint"],
                "checkpoint_sha256": report["checkpoint_sha256"],
                "action_mae": item["action_mae"],
                "gripper_sign_accuracy": item["gripper_sign_accuracy"],
            }
            for path, report, item in zip(args.report, reports, final, strict=True)
        ],
        "limitations": [
            "offline action error does not establish LIBERO rollout success",
            "the official raw HDF5 suite is filtered offline and is not the replay-regenerated RLDS release",
            "teacher-action and teacher-feature distillation are not included in these runs",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "action_mae": payload["action_mae"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
