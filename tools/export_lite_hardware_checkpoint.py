#!/usr/bin/env python3
"""Export a trained QAT checkpoint and one replay vector in the PL ABI."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.data.lite_libero_hdf5 import LiberoHdf5LiteDataset
from turbovla.lite_hardware_pack import export_hardware_checkpoint_pack
from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATS = ROOT / "experiments" / "libero" / "configs" / "libero_all4_stats.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--stats", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--stats-key", default="libero_all4_no_noops")
    parser.add_argument("--split", choices=("train", "validation"), default="validation")
    parser.add_argument("--split-seed", type=int, default=20260921)
    parser.add_argument("--sample-index", type=int, default=0)
    parser.add_argument("--expected-checkpoint-sha256")
    args = parser.parse_args()

    checkpoint_sha256 = _sha256(args.checkpoint)
    if args.expected_checkpoint_sha256 and checkpoint_sha256 != args.expected_checkpoint_sha256:
        raise ValueError(
            f"checkpoint SHA256 mismatch: expected {args.expected_checkpoint_sha256}, got {checkpoint_sha256}"
        )
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    config = LiteStudentConfig(**checkpoint["config"])
    model = TurboVLALiteStudent(config, checkpoint["quantization"]).eval()
    model.load_state_dict(checkpoint["state_dict"], strict=True)

    dataset = LiberoHdf5LiteDataset(
        args.dataset_dir,
        args.stats,
        stats_key=args.stats_key,
        split=args.split,
        seed=args.split_seed,
    )
    if not 0 <= args.sample_index < len(dataset):
        raise IndexError(f"sample index {args.sample_index} is outside dataset length {len(dataset)}")
    selected = dataset[args.sample_index]
    image = selected["image"].numpy()[None]
    state = selected["state"].numpy()[None]
    instruction_id = np.asarray([selected["instruction_id"].item()], dtype=np.uint16)
    with torch.no_grad():
        checkpoint_action = model(
            selected["image"][None],
            selected["state"][None],
            selected["instruction_id"][None],
        )["action"].numpy()

    dataset_manifest = dataset.manifest()
    manifest = export_hardware_checkpoint_pack(
        checkpoint,
        args.output_dir,
        checkpoint_sha256=checkpoint_sha256,
        image=image,
        state=state,
        instruction_id=instruction_id,
        sample={
            "dataset_index_sha256": dataset_manifest["index_sha256"],
            "dataset_samples": len(dataset),
            "index": args.sample_index,
            "split": args.split,
            "split_seed": args.split_seed,
            "task_name": selected["task_name"],
            "instruction": selected["instruction"],
            "normalized_state_max_abs": float(np.max(np.abs(state.astype(np.float32) / 1024.0))),
        },
        checkpoint_action=checkpoint_action,
    )
    manifest_path = args.output_dir / "manifest.json"
    print(
        json.dumps(
            {
                "checkpoint_sha256": manifest["source"]["checkpoint_sha256"],
                "manifest_sha256": _sha256(manifest_path),
                "model_sha256": manifest["files"]["model.bin"],
                "output": str(args.output_dir),
                "state_input_scale": manifest["state_input_scale"],
                "tensors": len(manifest["tensors"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
