#!/usr/bin/env python3
"""Compare a trained fake-QAT checkpoint with its exact exported PL model."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.data.lite_libero_hdf5 import LiberoHdf5LiteDataset
from turbovla.lite_hardware_pack import checkpoint_hardware_reference, load_hardware_reference
from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATS = ROOT / "experiments" / "libero" / "configs" / "libero_all4_stats.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _masked_mae(actual: np.ndarray, expected: np.ndarray, mask: np.ndarray) -> tuple[float, int]:
    errors = np.abs(actual - expected) * mask[..., None]
    values = int(mask.sum()) * actual.shape[-1]
    return float(errors.sum()), values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--pack-dir", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--stats", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--stats-key", default="libero_all4_no_noops")
    parser.add_argument("--split-seed", type=int, default=20260921)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 10:
        raise ValueError("at least 10 samples are required for task coverage")

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    config = LiteStudentConfig(**checkpoint["config"])
    model = TurboVLALiteStudent(config, checkpoint["quantization"]).eval()
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    source_reference = checkpoint_hardware_reference(checkpoint)
    pack_reference = load_hardware_reference(args.pack_dir)
    dataset = LiberoHdf5LiteDataset(
        args.dataset_dir,
        args.stats,
        stats_key=args.stats_key,
        split="validation",
        seed=args.split_seed,
    )

    sample_count = min(args.samples, len(dataset))
    indices = np.linspace(0, len(dataset) - 1, sample_count, dtype=np.int64)
    task_counts: Counter[int] = Counter()
    source_pack_max = 0.0
    source_pack_sum = 0.0
    fake_pack_max = 0.0
    fake_pack_sum = 0.0
    action_values = 0
    fake_gt_sum = 0.0
    pack_gt_sum = 0.0
    valid_action_values = 0
    fake_gripper_matches = 0
    pack_gripper_matches = 0
    valid_steps = 0
    normalized_state_max_abs = 0.0

    with torch.no_grad():
        for index in indices:
            selected = dataset[int(index)]
            image = selected["image"].numpy()[None]
            state = selected["state"].numpy()[None]
            instruction_id = np.asarray([selected["instruction_id"].item()], dtype=np.uint16)
            source = source_reference.run(image, state, instruction_id, mode="int8")["action"]
            packed = pack_reference.run(image, state, instruction_id, mode="int8")["action"]
            fake = model(
                selected["image"][None],
                selected["state"][None],
                selected["instruction_id"][None],
            )["action"].numpy()
            expected = selected["action_target"].numpy()[None]
            mask = selected["action_mask"].numpy()[None]

            source_pack = np.abs(source - packed)
            fake_pack = np.abs(fake - packed)
            source_pack_max = max(source_pack_max, float(source_pack.max()))
            source_pack_sum += float(source_pack.sum())
            fake_pack_max = max(fake_pack_max, float(fake_pack.max()))
            fake_pack_sum += float(fake_pack.sum())
            action_values += source.size
            normalized_state_max_abs = max(
                normalized_state_max_abs,
                float(np.max(np.abs(state.astype(np.float32) / 1024.0))),
            )

            total, values = _masked_mae(fake, expected, mask)
            fake_gt_sum += total
            pack_total, pack_values = _masked_mae(packed, expected, mask)
            pack_gt_sum += pack_total
            valid_action_values += values
            if values != pack_values:
                raise RuntimeError("fake-QAT and exact INT8 masks disagree")
            valid = mask.astype(bool)
            fake_gripper_matches += int(np.sum((np.sign(fake[..., 6]) == np.sign(expected[..., 6])) & valid))
            pack_gripper_matches += int(np.sum((np.sign(packed[..., 6]) == np.sign(expected[..., 6])) & valid))
            valid_steps += int(valid.sum())
            task_counts[int(instruction_id[0])] += 1

    if set(task_counts) != set(range(10)):
        raise RuntimeError(f"uniform validation sample did not cover all 10 instructions: {task_counts}")
    round_trip_max_threshold = 1.0e-6
    report = {
        "schema_version": 1,
        "result": "passed" if source_pack_max <= round_trip_max_threshold else "failed",
        "source": {
            "checkpoint": str(args.checkpoint),
            "checkpoint_sha256": _sha256(args.checkpoint),
            "manifest_sha256": _sha256(args.pack_dir / "manifest.json"),
            "model_sha256": _sha256(args.pack_dir / "model.bin"),
        },
        "dataset": {
            "index_sha256": dataset.index_sha256(),
            "samples": sample_count,
            "sampling": "uniform_indices_over_fixed_validation_split",
            "split_seed": args.split_seed,
            "task_counts": {str(key): task_counts[key] for key in sorted(task_counts)},
            "normalized_state_max_abs": normalized_state_max_abs,
        },
        "parity": {
            "source_exact_int8_to_exported_pack": {
                "max_abs_error": source_pack_max,
                "mean_abs_error": source_pack_sum / action_values,
                "max_abs_error_threshold": round_trip_max_threshold,
            },
            "checkpoint_fake_qat_to_exported_exact_int8": {
                "max_abs_error": fake_pack_max,
                "mean_abs_error": fake_pack_sum / action_values,
            },
        },
        "offline_metrics": {
            "checkpoint_fake_qat_action_mae": fake_gt_sum / valid_action_values,
            "exported_exact_int8_action_mae": pack_gt_sum / valid_action_values,
            "checkpoint_fake_qat_gripper_sign_accuracy": fake_gripper_matches / valid_steps,
            "exported_exact_int8_gripper_sign_accuracy": pack_gripper_matches / valid_steps,
            "valid_action_values": valid_action_values,
            "valid_steps": valid_steps,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
