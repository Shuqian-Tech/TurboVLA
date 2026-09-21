#!/usr/bin/env python3
"""Calibrate TurboVLA-Lite activation and weight scales from a trained checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.data.lite_libero_hdf5 import LiberoHdf5LiteDataset
from turbovla.lite_reference import load_contract
from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATS = ROOT / "experiments" / "libero" / "configs" / "libero_all4_stats.json"
ACTIVATION_NAMES = (
    "image_normalized",
    "visual_conv",
    "visual_tokens",
    "language_embedding",
    "fusion_0",
    "fusion_1",
    "state_projection",
    "action_hidden",
    "action",
)


def _scale(value: torch.Tensor) -> float:
    return max(float(value.detach().abs().max().cpu()) / 127.0, 1.0e-8)


def _module_scale(modules: torch.nn.Module | torch.nn.ModuleList) -> float:
    if isinstance(modules, torch.nn.ModuleList):
        maximum = max(float(module.weight.detach().abs().max().cpu()) for module in modules)
    else:
        maximum = float(modules.weight.detach().abs().max().cpu())
    return max(maximum / 127.0, 1.0e-8)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--stats", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--stats-key", default="libero_all4_no_noops")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--batches", type=int, default=0, help="0 uses the complete validation split")
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument("--split-seed", type=int, default=20260921)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint-output", type=Path)
    args = parser.parse_args()
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA calibration requested but CUDA is unavailable")

    saved = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    contract = load_contract()
    saved_config = LiteStudentConfig(**saved["config"])
    contract_config = LiteStudentConfig.from_contract(contract)
    for field in ("hidden_dim", "visual_tokens", "state_dim", "action_horizon", "action_dim"):
        if getattr(saved_config, field) != getattr(contract_config, field):
            raise ValueError(f"checkpoint {field} does not match the Lite contract")
    config = replace(saved_config, fake_quant=False)
    model = TurboVLALiteStudent(config).to(device)
    incompatible = model.load_state_dict(saved["state_dict"], strict=False)
    unexpected = [name for name in incompatible.unexpected_keys if not name.endswith(".scale")]
    if incompatible.missing_keys or unexpected:
        raise RuntimeError(
            f"checkpoint is incompatible: missing={incompatible.missing_keys}, unexpected={unexpected}"
        )
    model.eval()

    dataset = LiberoHdf5LiteDataset(
        args.dataset_dir,
        args.stats,
        stats_key=args.stats_key,
        split="validation",
        validation_fraction=args.validation_fraction,
        seed=args.split_seed,
    )
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
        persistent_workers=args.num_workers > 0,
    )
    activation_names = list(ACTIVATION_NAMES)
    if config.visual_encoder == "depthwise_separable":
        activation_names.extend(("spatial_0", "spatial_1"))
    maxima = {name: 0.0 for name in activation_names}
    state_maximum = 0.0
    samples = 0
    with torch.no_grad():
        for batch_index, batch in enumerate(loader):
            if args.batches and batch_index >= args.batches:
                break
            image = batch["image"].to(device, non_blocking=True)
            state = batch["state"].to(device, non_blocking=True)
            instruction_id = batch["instruction_id"].to(device, non_blocking=True)
            outputs = model(image, state, instruction_id)
            for name in activation_names:
                maxima[name] = max(maxima[name], float(outputs[name].abs().max().cpu()))
            state_maximum = max(
                state_maximum,
                float((state.float() * config.state_normalization).abs().max().cpu()),
            )
            samples += image.shape[0]
    if samples == 0:
        raise RuntimeError("calibration dataset produced no samples")

    activation_scales = {name: max(maximum / 127.0, 1.0e-8) for name, maximum in maxima.items()}
    weights = {
        "conv_weight": _module_scale(model.conv),
        "visual_projection": _module_scale(model.visual_projection),
        "instruction_table": _scale(model.instruction_embedding.weight),
        "fusion_visual": _module_scale(model.fusion_visual),
        "fusion_language": _module_scale(model.fusion_language),
        "fusion_gate": _module_scale(model.fusion_gate),
        "state_projection": _module_scale(model.state_projection),
        "action_input": _module_scale(model.action_input),
        "action_output": _module_scale(model.action_output),
    }
    if config.visual_encoder == "depthwise_separable":
        weights.update(
            {
                "spatial_depthwise": _module_scale(model.spatial_depthwise),
                "spatial_pointwise": _module_scale(model.spatial_pointwise),
            }
        )
    payload = {
        "activations": activation_scales,
        "weights": weights,
        "state_input": max(state_maximum / 127.0, 1.0e-8),
        "state_normalization": config.state_normalization,
        "calibration": {
            "checkpoint": str(args.checkpoint),
            "dataset": dataset.manifest(),
            "samples": samples,
            "device": str(device),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {"output": str(args.output), "samples": samples}
    if args.checkpoint_output is not None:
        ptq_config = replace(config, fake_quant=True)
        ptq_model = TurboVLALiteStudent(ptq_config, payload)
        incompatible = ptq_model.load_state_dict(saved["state_dict"], strict=False)
        invalid_missing = [name for name in incompatible.missing_keys if not name.endswith(".scale")]
        if invalid_missing or incompatible.unexpected_keys:
            raise RuntimeError(
                "checkpoint is incompatible with PTQ export: "
                f"missing={invalid_missing}, unexpected={incompatible.unexpected_keys}"
            )
        ptq_checkpoint = dict(saved)
        ptq_checkpoint.update(
            {
                "state_dict": ptq_model.state_dict(),
                "config": ptq_config.to_dict(),
                "quantization": payload,
                "mode": "ptq",
            }
        )
        args.checkpoint_output.parent.mkdir(parents=True, exist_ok=True)
        torch.save(ptq_checkpoint, args.checkpoint_output)
        result["checkpoint_output"] = str(args.checkpoint_output)
        result["checkpoint_sha256"] = hashlib.sha256(args.checkpoint_output.read_bytes()).hexdigest()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
