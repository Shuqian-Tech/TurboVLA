#!/usr/bin/env python3
"""Train TurboVLA-Lite with action and teacher-feature distillation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.lite_reference import TurboVLALiteReference, deterministic_sample, load_contract
from turbovla.lite_student import LiteStudentConfig, TurboVLALiteStudent, lite_distillation_loss

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CALIBRATION = ROOT / "tests" / "data" / "lite_golden" / "calibration.json"


def _smoke_batch(model: TurboVLALiteReference, count: int) -> dict[str, np.ndarray]:
    image, state, instruction_id = deterministic_sample(model.contract)
    images = np.repeat(image, count, axis=0)
    states = np.repeat(state, count, axis=0)
    ids = np.repeat(instruction_id, count, axis=0)
    states[:, 0] += np.arange(count, dtype=np.int16) * 8
    teacher = model.run(images[:1], states[:1], ids[:1])
    teacher_action = np.repeat(teacher["action"], count, axis=0)
    teacher_visual = np.repeat(teacher["visual_tokens"], count, axis=0)
    action_target = np.clip(teacher_action + (np.arange(count)[:, None, None] % 3 - 1) * 0.01, -1.0, 1.0)
    return {
        "image": images,
        "state": states,
        "instruction_id": ids,
        "action_target": action_target.astype(np.float32),
        "teacher_action": teacher_action.astype(np.float32),
        "teacher_visual_tokens": teacher_visual.astype(np.float32),
    }


def _load_dataset(path: Path, contract: dict) -> dict[str, np.ndarray]:
    with np.load(path) as data:
        required = {"image", "state", "instruction_id", "action_target", "teacher_action", "teacher_visual_tokens"}
        missing = sorted(required - set(data.files))
        if missing:
            raise ValueError(f"student dataset is missing required arrays: {missing}")
        arrays = {name: np.asarray(data[name]) for name in required}
    expected = {
        "image": (1, 1, 3, 128, 128),
        "state": (1, 8),
        "instruction_id": (1,),
        "action_target": (1, 12, 7),
        "teacher_action": (1, 12, 7),
        "teacher_visual_tokens": (1, 32, 128),
    }
    for name, suffix in expected.items():
        if arrays[name].ndim != len(suffix) or tuple(arrays[name].shape[1:]) != suffix[1:]:
            raise ValueError(f"{name} must have sample shape {suffix}, got {arrays[name].shape}")
    if (
        arrays["image"].dtype != np.uint8
        or arrays["state"].dtype != np.int16
        or arrays["instruction_id"].dtype != np.uint16
    ):
        raise ValueError("image/state/instruction_id dtypes must be uint8/int16/uint16")
    if len({len(value) for value in arrays.values()}) != 1:
        raise ValueError("all student dataset arrays must have the same sample count")
    return arrays


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dataset", type=Path)
    source.add_argument("--smoke", action="store_true", help="train on deterministic contract samples")
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--output", type=Path, default=Path("build/lite/student.pt"))
    parser.add_argument("--report", type=Path, default=Path("build/lite/student_training_report.json"))
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260919)
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1:
        raise SystemExit("--steps and --batch-size must be positive")

    torch.manual_seed(args.seed)
    contract = load_contract()
    reference = TurboVLALiteReference(contract)
    arrays = _smoke_batch(reference, max(args.batch_size, 4)) if args.smoke else _load_dataset(args.dataset, contract)
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    config = LiteStudentConfig.from_contract(contract, args.calibration)
    student = TurboVLALiteStudent(config, calibration)
    optimizer = torch.optim.AdamW(student.parameters(), lr=2e-3, weight_decay=1e-5)
    tensors = [
        torch.from_numpy(arrays["image"]),
        torch.from_numpy(arrays["state"]),
        torch.from_numpy(arrays["instruction_id"].astype(np.int64)),
        torch.from_numpy(arrays["action_target"]),
        torch.from_numpy(arrays["teacher_action"]),
        torch.from_numpy(arrays["teacher_visual_tokens"]),
    ]
    loader = DataLoader(TensorDataset(*tensors), batch_size=args.batch_size, shuffle=False)
    first_metrics: dict[str, float] | None = None
    last_metrics: dict[str, float] = {}
    step = 0
    student.train()
    while step < args.steps:
        for batch in loader:
            image, state, instruction_id, action_target, teacher_action, teacher_visual = batch
            outputs = student(image, state, instruction_id)
            loss, metrics = lite_distillation_loss(outputs, action_target, teacher_action, teacher_visual, config)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0)
            optimizer.step()
            step += 1
            first_metrics = first_metrics or metrics
            last_metrics = metrics
            if step >= args.steps:
                break

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": student.state_dict(),
            "config": config.to_dict(),
            "quantization": calibration,
            "contract": contract,
        },
        args.output,
    )
    report = {
        "contract_version": contract["contract_version"],
        "dataset_mode": "smoke" if args.smoke else "external_npz",
        "samples": len(arrays["image"]),
        "steps": step,
        "parameter_count": sum(parameter.numel() for parameter in student.parameters()),
        "input_shape": [1, 1, 3, 128, 128],
        "action_shape": [1, 12, 7],
        "initial": first_metrics,
        "final": last_metrics,
        "checkpoint": str(args.output),
    }
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
