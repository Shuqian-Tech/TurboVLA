#!/usr/bin/env python3
"""Train and evaluate the hardware-equivalent TurboVLA-Lite student on CUDA."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.data.lite_libero_hdf5 import LiberoHdf5LiteDataset
from turbovla.lite_reference import load_contract
from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATS = ROOT / "experiments" / "libero" / "configs" / "libero_all4_stats.json"
DEFAULT_CALIBRATION = ROOT / "tests" / "data" / "lite_golden" / "calibration.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--stats", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--stats-key", default="libero_all4_no_noops")
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--mode", choices=("fp32", "qat"), default="fp32")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=2.0e-3)
    parser.add_argument("--weight-decay", type=float, default=1.0e-5)
    parser.add_argument("--gripper-loss-weight", type=float, default=1.0)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--validation-batches", type=int, default=0, help="0 evaluates the complete validation split")
    parser.add_argument("--eval-interval", type=int, default=100)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--max-train-samples", type=int)
    parser.add_argument("--max-validation-samples", type=int)
    parser.add_argument("--overfit-samples", type=int, help="train and validate on the same first N filtered samples")
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument("--split-seed", type=int, default=20260921)
    parser.add_argument("--dataset-revision", default="unknown")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("build/lite/gpu_student.pt"))
    parser.add_argument("--report", type=Path, default=Path("build/lite/gpu_evaluation.json"))
    args = parser.parse_args()
    for name in ("steps", "batch_size", "eval_interval"):
        if getattr(args, name.replace("-", "_")) < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.num_workers < 0 or args.validation_batches < 0:
        parser.error("--num-workers and --validation-batches cannot be negative")
    if args.eval_only and args.resume is None:
        parser.error("--eval-only requires --resume")
    if args.overfit_samples is not None and args.overfit_samples < 1:
        parser.error("--overfit-samples must be positive")
    if args.gripper_loss_weight <= 0:
        parser.error("--gripper-loss-weight must be positive")
    return args


def _resolve_device(requested: str) -> torch.device:
    device = torch.device(requested)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but torch.cuda.is_available() is false; CPU fallback is prohibited")
    return device


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _limit(dataset: LiberoHdf5LiteDataset, maximum: int | None) -> LiberoHdf5LiteDataset | Subset:
    if maximum is None or maximum >= len(dataset):
        return dataset
    if maximum < 1:
        raise ValueError("sample limits must be positive")
    return Subset(dataset, range(maximum))


def _masked_action_l1(
    prediction: torch.Tensor,
    target: torch.Tensor,
    action_mask: torch.Tensor,
    gripper_loss_weight: float,
) -> torch.Tensor:
    mask = action_mask[:, :, None]
    weights = torch.ones(prediction.shape[-1], dtype=prediction.dtype, device=prediction.device)
    weights[-1] = gripper_loss_weight
    denominator = mask.sum() * weights.sum()
    return (torch.abs(prediction - target) * mask * weights).sum() / denominator.clamp_min(1.0)


@torch.no_grad()
def _evaluate(
    model: TurboVLALiteStudent,
    loader: DataLoader,
    device: torch.device,
    max_batches: int,
) -> dict:
    model.eval()
    absolute_sum = 0.0
    absolute_count = 0.0
    maximum = 0.0
    samples = 0
    dimension_sum = torch.zeros(7, dtype=torch.float64)
    dimension_count = torch.zeros(7, dtype=torch.float64)
    gripper_correct = 0
    gripper_count = 0
    per_task: dict[str, dict[str, float]] = {}
    for batch_index, batch in enumerate(loader):
        if max_batches and batch_index >= max_batches:
            break
        image = batch["image"].to(device, non_blocking=True)
        state = batch["state"].to(device, non_blocking=True)
        instruction_id = batch["instruction_id"].to(device, non_blocking=True)
        target = batch["action_target"].to(device, non_blocking=True)
        mask = batch["action_mask"].to(device, non_blocking=True)[:, :, None]
        prediction = model(image, state, instruction_id)["action"]
        error = torch.abs(prediction - target) * mask
        absolute_sum += float(error.sum().cpu())
        absolute_count += float(mask.sum().cpu()) * error.shape[-1]
        maximum = max(maximum, float(error.max().cpu()))
        samples += image.shape[0]
        dimension_sum += error.sum(dim=(0, 1)).cpu().double()
        dimension_count += mask.sum(dim=(0, 1)).cpu().double()
        valid_gripper = mask[:, :, 0].bool()
        prediction_gripper = prediction[:, :, 6]
        gripper_correct += int(
            (torch.sign(prediction_gripper[valid_gripper]) == torch.sign(target[:, :, 6][valid_gripper])).sum().cpu()
        )
        gripper_count += int(valid_gripper.sum().cpu())
        sample_mae = error.sum(dim=(1, 2)) / (mask.sum(dim=(1, 2)) * error.shape[-1]).clamp_min(1.0)
        for task_name, value in zip(batch["task_name"], sample_mae.cpu().tolist(), strict=True):
            entry = per_task.setdefault(task_name, {"sum": 0.0, "samples": 0.0})
            entry["sum"] += float(value)
            entry["samples"] += 1.0
    if absolute_count == 0:
        raise RuntimeError("validation loader produced no valid action values")
    return {
        "action_mae": absolute_sum / absolute_count,
        "action_max_abs_error": maximum,
        "action_dimension_mae": (dimension_sum / dimension_count.clamp_min(1.0)).tolist(),
        "gripper_sign_accuracy": gripper_correct / max(gripper_count, 1),
        "samples": samples,
        "per_task_action_mae": {
            task: values["sum"] / values["samples"] for task, values in sorted(per_task.items())
        },
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = _parse_args()
    device = _resolve_device(args.device)
    _seed_everything(args.seed)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)

    if args.overfit_samples is not None:
        train_base = LiberoHdf5LiteDataset(
            args.dataset_dir,
            args.stats,
            stats_key=args.stats_key,
            split="all",
            validation_fraction=args.validation_fraction,
            seed=args.split_seed,
        )
        validation_base = train_base
        shared_samples = min(args.overfit_samples, len(train_base))
        train_data = Subset(train_base, range(shared_samples))
        validation_data = Subset(validation_base, range(shared_samples))
    else:
        train_base = LiberoHdf5LiteDataset(
            args.dataset_dir,
            args.stats,
            stats_key=args.stats_key,
            split="train",
            validation_fraction=args.validation_fraction,
            seed=args.split_seed,
        )
        validation_base = LiberoHdf5LiteDataset(
            args.dataset_dir,
            args.stats,
            stats_key=args.stats_key,
            split="validation",
            validation_fraction=args.validation_fraction,
            seed=args.split_seed,
        )
        train_data = _limit(train_base, args.max_train_samples)
        validation_data = _limit(validation_base, args.max_validation_samples)
    generator = torch.Generator().manual_seed(args.seed)
    loader_kwargs = {
        "batch_size": args.batch_size,
        "num_workers": args.num_workers,
        "pin_memory": device.type == "cuda",
        "persistent_workers": args.num_workers > 0,
    }
    train_loader = DataLoader(train_data, shuffle=True, generator=generator, **loader_kwargs)
    validation_loader = DataLoader(validation_data, shuffle=False, **loader_kwargs)

    contract = load_contract()
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    config = replace(LiteStudentConfig.from_contract(contract, args.calibration), fake_quant=args.mode == "qat")
    model = TurboVLALiteStudent(config, calibration if args.mode == "qat" else None).to(device)
    if args.resume is not None:
        saved = torch.load(args.resume, map_location="cpu", weights_only=False)
        incompatible = model.load_state_dict(saved["state_dict"], strict=False)
        invalid_missing = [name for name in incompatible.missing_keys if not name.endswith(".scale")]
        invalid_unexpected = [name for name in incompatible.unexpected_keys if not name.endswith(".scale")]
        if invalid_missing or invalid_unexpected:
            raise RuntimeError(
                f"checkpoint is incompatible: missing={invalid_missing}, unexpected={invalid_unexpected}"
            )
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)

    started = time.monotonic()
    curve = [{"step": 0, "validation": _evaluate(model, validation_loader, device, args.validation_batches)}]
    train_iterator = iter(train_loader)
    train_loss_sum = 0.0
    train_samples = 0
    steps_to_run = 0 if args.eval_only else args.steps
    model.train()
    for step in range(1, steps_to_run + 1):
        try:
            batch = next(train_iterator)
        except StopIteration:
            train_iterator = iter(train_loader)
            batch = next(train_iterator)
        image = batch["image"].to(device, non_blocking=True)
        state = batch["state"].to(device, non_blocking=True)
        instruction_id = batch["instruction_id"].to(device, non_blocking=True)
        action_target = batch["action_target"].to(device, non_blocking=True)
        action_mask = batch["action_mask"].to(device, non_blocking=True)
        outputs = model(image, state, instruction_id)
        loss = _masked_action_l1(
            outputs["action"], action_target, action_mask, args.gripper_loss_weight
        )
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        train_loss_sum += float(loss.detach().cpu()) * image.shape[0]
        train_samples += image.shape[0]
        if step % args.eval_interval == 0 or step == steps_to_run:
            validation = _evaluate(model, validation_loader, device, args.validation_batches)
            curve.append(
                {
                    "step": step,
                    "train_action_l1": train_loss_sum / train_samples,
                    "validation": validation,
                }
            )
            print(json.dumps(curve[-1], sort_keys=True), flush=True)
            train_loss_sum = 0.0
            train_samples = 0
            model.train()

    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elapsed = time.monotonic() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.eval_only:
        checkpoint_path = args.resume
    else:
        checkpoint = {
            "state_dict": {name: value.detach().cpu() for name, value in model.state_dict().items()},
            "config": config.to_dict(),
            "quantization": calibration if args.mode == "qat" else None,
            "contract": contract,
            "instructions": train_base.manifest()["instructions"],
            "dataset_revision": args.dataset_revision,
            "seed": args.seed,
            "mode": args.mode,
        }
        torch.save(checkpoint, args.output)
        checkpoint_path = args.output
    report = {
        "contract_version": contract["contract_version"],
        "mode": args.mode,
        "seed": args.seed,
        "split_seed": args.split_seed,
        "device_requested": args.device,
        "device": str(device),
        "cuda": {
            "available": torch.cuda.is_available(),
            "runtime": torch.version.cuda,
            "device_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
            "peak_memory_bytes": torch.cuda.max_memory_allocated(device) if device.type == "cuda" else 0,
        },
        "dataset_revision": args.dataset_revision,
        "train_dataset": train_base.manifest(),
        "validation_dataset": validation_base.manifest(),
        "train_samples_used": len(train_data),
        "validation_samples_used": len(validation_data),
        "overfit_samples": args.overfit_samples,
        "steps": steps_to_run,
        "eval_only": args.eval_only,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "gripper_loss_weight": args.gripper_loss_weight,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "elapsed_seconds": elapsed,
        "samples_per_second": steps_to_run * args.batch_size / elapsed if steps_to_run else None,
        "curve": curve,
        "checkpoint": str(checkpoint_path),
    }
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["checkpoint_sha256"] = _sha256(checkpoint_path)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "final": curve[-1]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
