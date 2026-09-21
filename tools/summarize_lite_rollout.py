#!/usr/bin/env python3
"""Summarize matched TurboVLA-Lite LIBERO rollout pilots."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def _wilson(successes: int, episodes: int, z: float = 1.959963984540054) -> list[float]:
    if episodes <= 0:
        raise ValueError("episode count must be positive")
    rate = successes / episodes
    denominator = 1.0 + z * z / episodes
    center = (rate + z * z / (2.0 * episodes)) / denominator
    margin = z * math.sqrt(rate * (1.0 - rate) / episodes + z * z / (4.0 * episodes * episodes))
    margin /= denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def _parse_result(value: str) -> tuple[str, Path]:
    label, separator, path = value.partition("=")
    if not separator or not label or not path:
        raise argparse.ArgumentTypeError("--result must use LABEL=PATH")
    return label, Path(path)


def _checkpoint_sha256(payload: dict) -> str | None:
    recorded = payload.get("checkpoint_sha256")
    if recorded:
        return str(recorded)
    path = Path(payload["ckpt_path"])
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=_parse_result, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scope", default="libero_spatial_closed_loop_pilot")
    parser.add_argument("--decision-status", default="preliminary_tune")
    args = parser.parse_args()
    if len(args.result) < 2:
        parser.error("at least two matched rollout results are required")

    loaded = [(label, path, json.loads(path.read_text(encoding="utf-8"))) for label, path in args.result]
    suites = {payload["task_suite_name"] for _, _, payload in loaded}
    seeds = {payload["seed"] for _, _, payload in loaded}
    task_ids = [[task["task_id"] for task in payload["tasks"]] for _, _, payload in loaded]
    episode_counts = [[task["episodes"] for task in payload["tasks"]] for _, _, payload in loaded]
    open_loop_steps = {payload["num_open_loop_steps"] for _, _, payload in loaded}
    if len(suites) != 1 or len(seeds) != 1 or len(open_loop_steps) != 1:
        raise ValueError("rollout results must share suite, seed, and open-loop horizon")
    task_ids_mismatch = any(ids != task_ids[0] for ids in task_ids[1:])
    episode_counts_mismatch = any(counts != episode_counts[0] for counts in episode_counts[1:])
    if task_ids_mismatch or episode_counts_mismatch:
        raise ValueError("rollout results must cover identical task IDs and episode counts")

    matched_episode_counts = episode_counts[0]
    if len(set(matched_episode_counts)) == 1:
        sampling_limitation = (
            f"{matched_episode_counts[0]} episodes per task still yield wide task-level confidence intervals"
        )
    else:
        sampling_limitation = "the limited per-task episode counts yield wide task-level confidence intervals"

    baseline_rate = loaded[0][2]["overall_success_rate"]
    runs = []
    for label, path, payload in loaded:
        tasks = []
        for task in payload["tasks"]:
            tasks.append(
                {
                    **task,
                    "wilson_95_interval": _wilson(task["successes"], task["episodes"]),
                }
            )
        rate = payload["overall_success_rate"]
        runs.append(
            {
                "label": label,
                "source": str(path),
                "checkpoint": payload["ckpt_path"],
                "checkpoint_sha256": _checkpoint_sha256(payload),
                "successes": payload["total_successes"],
                "episodes": payload["total_episodes"],
                "success_rate": rate,
                "wilson_95_interval": _wilson(payload["total_successes"], payload["total_episodes"]),
                "absolute_delta_from_baseline": rate - baseline_rate,
                "tasks": tasks,
            }
        )

    summary = {
        "schema_version": "1.0.0",
        "scope": args.scope,
        "decision_status": args.decision_status,
        "deployment_claim": "none",
        "protocol": {
            "suite": next(iter(suites)),
            "seed": next(iter(seeds)),
            "task_ids": task_ids[0],
            "episodes_per_task": episode_counts[0],
            "open_loop_steps": next(iter(open_loop_steps)),
        },
        "runs": runs,
        "limitations": [
            sampling_limitation,
            "the same fixed initial states are used for matched FP32 and quantized comparisons",
            "simulation success does not establish real-robot transfer or KR260 deployment accuracy",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "runs": len(runs)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
