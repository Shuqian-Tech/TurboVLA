#!/usr/bin/env python3
"""Cache official TurboVLA actions and relational visual targets for Lite."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from numpy.lib.format import open_memmap
from PIL import Image
from torch.utils.data import DataLoader, Subset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.data.lite_libero_hdf5 import LiberoHdf5LiteDataset
from turbovla.distillation import CACHE_SCHEMA_VERSION
from turbovla.evaluation.policy import TurboVLAPolicy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATS = ROOT / "experiments" / "libero" / "configs" / "libero_all4_stats.json"
DEFAULT_CHECKPOINT = ROOT / "data" / "teacher" / "TurboVLA" / "checkpoints" / "libero" / "turbovla_libero.pth"
DEFAULT_DINOV3 = ROOT / "data" / "teacher" / "dinov3-vitb16"
DEFAULT_BERT = ROOT / "data" / "teacher" / "bert-base-uncased"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--stats", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--stats-key", default="libero_all4_no_noops")
    parser.add_argument("--split", choices=("train", "validation"), required=True)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--split-seed", type=int, default=20260921)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--dinov3-path", type=Path, default=DEFAULT_DINOV3)
    parser.add_argument("--bert-path", type=Path, default=DEFAULT_BERT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1 or args.num_workers < 0:
        parser.error("--batch-size must be positive and --num-workers cannot be negative")
    return args


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _resize_batch(images: torch.Tensor) -> list[np.ndarray]:
    arrays = images.permute(0, 2, 3, 1).cpu().numpy()
    return [
        np.asarray(Image.fromarray(image).resize((256, 256), Image.Resampling.BILINEAR))
        for image in arrays
    ]


def main() -> int:
    args = _parse_args()
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable; CPU fallback is prohibited")

    dataset = LiberoHdf5LiteDataset(
        args.dataset_dir,
        args.stats,
        stats_key=args.stats_key,
        split=args.split,
        validation_fraction=args.validation_fraction,
        seed=args.split_seed,
        include_teacher_observations=True,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    action_path = args.output_dir / "teacher_action.npy"
    relation_path = args.output_dir / "teacher_visual_relation.npy"
    progress_path = args.output_dir / "progress.json"
    metadata_path = args.output_dir / "metadata.json"
    checkpoint_sha256 = _sha256(args.checkpoint)
    identity = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "split": args.split,
        "samples": len(dataset),
        "dataset_index_sha256": dataset.index_sha256(),
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_sha256": checkpoint_sha256,
        "split_seed": args.split_seed,
        "validation_fraction": args.validation_fraction,
    }
    dataset_manifest = dataset.manifest()

    completed = 0
    if args.resume:
        if not progress_path.is_file():
            raise FileNotFoundError(f"resume progress is missing: {progress_path}")
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if any(progress.get(key) != value for key, value in identity.items()):
            raise ValueError("resume metadata does not match the requested teacher cache")
        completed = int(progress["completed_samples"])
        actions = open_memmap(action_path, mode="r+")
        relations = open_memmap(relation_path, mode="r+")
    else:
        if any(path.exists() for path in (action_path, relation_path, progress_path, metadata_path)):
            raise FileExistsError(f"teacher cache output is not empty: {args.output_dir}")
        actions = open_memmap(action_path, mode="w+", dtype=np.float16, shape=(len(dataset), 12, 7))
        relations = open_memmap(
            relation_path,
            mode="w+",
            dtype=np.float16,
            shape=(len(dataset), 32, 32),
        )
        _write_json(progress_path, {**identity, "completed_samples": 0, "status": "in_progress"})

    if completed < 0 or completed > len(dataset):
        raise ValueError(f"invalid completed sample count: {completed}")
    run_start = completed
    started = time.monotonic()
    if completed < len(dataset):
        subset = Subset(dataset, range(completed, len(dataset)))
        loader = DataLoader(
            subset,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.num_workers,
            pin_memory=device.type == "cuda",
            persistent_workers=args.num_workers > 0,
        )
        teacher = TurboVLAPolicy(
            ckpt_path=str(args.checkpoint),
            dinov3_path=str(args.dinov3_path),
            bert_path=str(args.bert_path),
            device=device,
            precision="bf16",
            verbose=True,
        )
        for batch_index, batch in enumerate(loader):
            primary = _resize_batch(batch["image"][:, 0])
            wrist = _resize_batch(batch["teacher_wrist_image"])
            states = [value.numpy() for value in batch["teacher_raw_state"]]
            targets = teacher.predict_distillation_targets_batch(
                primary,
                wrist,
                list(batch["instruction"]),
                states,
            )
            if not all(np.isfinite(value).all() for value in targets.values()):
                raise RuntimeError(f"teacher produced non-finite targets at sample {completed}")
            batch_size = len(primary)
            stop = completed + batch_size
            actions[completed:stop] = targets["teacher_action"].astype(np.float16)
            relations[completed:stop] = targets["teacher_visual_relation"].astype(np.float16)
            completed = stop
            if batch_index % 10 == 0 or completed == len(dataset):
                actions.flush()
                relations.flush()
                _write_json(
                    progress_path,
                    {**identity, "completed_samples": completed, "status": "in_progress"},
                )
                elapsed = time.monotonic() - started
                rate = ((completed - run_start) / elapsed) if elapsed else 0.0
                print(
                    json.dumps(
                        {
                            "completed": completed,
                            "samples": len(dataset),
                            "samples_per_second_since_start": rate,
                        }
                    ),
                    flush=True,
                )

    elapsed = time.monotonic() - started
    previous_metadata = (
        json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    )
    metadata = {
        **identity,
        "dataset_manifest": dataset_manifest,
        "teacher_precision": "bf16",
        "source_image_size": [128, 128],
        "teacher_image_size": [256, 256],
        "resize": "PIL bilinear",
        "feature_target": "primary-view post-language-fusion 16x16 tokens pooled to 4x8 cosine relation",
        "action_dtype": "float16",
        "visual_relation_dtype": "float16",
        "generation_elapsed_seconds": previous_metadata.get(
            "generation_elapsed_seconds",
            previous_metadata.get("elapsed_seconds", elapsed),
        ),
        "generation_samples_per_second": previous_metadata.get(
            "generation_samples_per_second",
            previous_metadata.get(
                "samples_per_second",
                (completed - run_start) / elapsed if elapsed else None,
            ),
        ),
        "teacher_action_sha256": _sha256(action_path),
        "teacher_visual_relation_sha256": _sha256(relation_path),
    }
    _write_json(metadata_path, metadata)
    _write_json(progress_path, {**identity, "completed_samples": completed, "status": "complete"})
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
