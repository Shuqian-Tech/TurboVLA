# T014 GPU TinyCNN Pilot Evidence

## Scope

This report measures the learning capacity of the exact 148,436-parameter
TurboVLA-Lite hardware contract. CUDA is used only for offline training and
evaluation. Deployment remains KR260/K26 PL inference with no GPU, DPU, or CPU
inference fallback.

The report contains both the original behavior-cloning baseline and a
teacher-action plus relational-feature distillation pilot. The student model
and FPGA inference contract are unchanged.

## Environment and data

- GPU: NVIDIA GeForce RTX 3070, 8192 MiB
- PyTorch: 2.14.0+cu130; CUDA runtime 13.0
- LIBERO source: commit `8f1084e3132a39270c3a13ebe37270a43ece2a01`
- `libero_spatial` HDF5 revision: `e329580e402fb5f07ae3b1f18475fc3b63783b91`
- TurboVLA teacher revision: `cb5300544693013164c4bb251a13036002a55c81`
- Teacher checkpoint SHA256: `d031ad7be05a2f5d04afb3194ed26b0cb46083685edee7a5e145078a37d26bab`
- Split seed: `20260921`, split by demonstration to avoid trajectory leakage
- Filtered samples: 51,109 train and 11,044 validation
- Input/output: one 128x128 RGB view, 8-D state, instruction ID, 12x7 action chunk

## Offline results

Three FP32 seeds used the same split and 2,000 update steps:

| Metric | Result |
|---|---:|
| Validation action MAE, mean | 0.127903 |
| Validation action MAE, population std | 0.000432 |
| Gripper sign accuracy, mean | 92.52% |
| Gripper sign accuracy, population std | 0.12 percentage points |
| Seed 20260921 throughput | 3,192 samples/s |
| Peak CUDA memory observed in fixed-split evaluation | 581 MiB |

Quantization on seed `20260921`:

| Mode | Validation MAE | Gripper sign accuracy |
|---|---:|---:|
| FP32 | 0.127495 | 92.45% |
| PTQ fake INT8 | 0.130040 | 92.46% |
| QAT fake INT8 | 0.128612 | 92.43% |

The 256-sample overfit diagnostic reached MAE `0.04239` and 98.06% gripper
sign accuracy. The 32-sample diagnostic reached MAE `0.04505`; increasing the
gripper loss weight improved its gripper sign accuracy from 92.71% to 96.09%.
The student learns strong signal but does not cleanly memorize the smallest set.

Machine-readable offline evidence is in
[`tests/data/lite_gpu_evaluation_report.json`](../../tests/data/lite_gpu_evaluation_report.json).

## Distillation pilot

The official teacher generated targets for all 51,109 train and 11,044
validation samples. The cache stores normalized 12x7 teacher actions and a
channel-independent visual target: primary-view, post-language-fusion 16x16
teacher tokens are pooled to 4x8 and converted to a 32x32 cosine relation
matrix. The student matches that matrix from `fusion_1`, so distillation adds
no inference parameters or FPGA operators.

The loss weights were ground-truth action `1.0`, teacher action `1.0`, and
feature relation `0.1`. FP32 distillation resumed the baseline for 2,000 steps
at learning rate `5e-4`; QAT then ran 500 steps at `2e-3`.

| Metric | Before | Distilled |
|---|---:|---:|
| Validation action MAE, FP32 | 0.127495 | 0.126056 |
| Validation teacher-action MAE, FP32 | 0.103029 | 0.077485 |
| Validation feature relation MSE, FP32 | 0.011283 | 0.005770 |
| Validation action MAE, PTQ | 0.130040 | 0.130382 |
| Validation action MAE, QAT | 0.128612 | 0.128996 |

The distilled FP32 checkpoint has SHA256
`dce6da5c26a4f06e5121ab7e0efee88cfc459c0aacfc9633e00c9c3ecde4a03a`.
The distilled PTQ and QAT checkpoint hashes are
`38f783732d01272b8b5a7831ef82afebb03e86229524061079fca8eb01fc9a97` and
`7209a40065aa72628bd1a2b3b92d92a205ac97a4bb1a4577c1e4eda3d5d5dc1a`.

## Closed-loop pilot

The matched pilot uses all 10 `libero_spatial` tasks, the first 3 fixed initial
states per task, seed 7, and 12 open-loop actions per prediction.

| Mode | Successes | Rate | Wilson 95% interval | Delta from FP32 |
|---|---:|---:|---:|---:|
| FP32 | 22/30 | 73.33% | 55.55%-85.82% | 0.00 pp |
| PTQ fake INT8 | 18/30 | 60.00% | 42.32%-75.41% | -13.33 pp |
| QAT fake INT8 | 19/30 | 63.33% | 45.51%-78.13% | -10.00 pp |
| TurboVLA teacher BF16 | 30/30 | 100.00% | 88.65%-100.00% | +26.67 pp |
| Distilled FP32 | 24/30 | 80.00% | 62.69%-90.50% | +6.67 pp |
| Distilled PTQ fake INT8 | 22/30 | 73.33% | 55.55%-85.82% | 0.00 pp |
| Distilled QAT fake INT8 | 23/30 | 76.67% | 59.07%-88.21% | +3.33 pp |

The intervals overlap and three episodes per task are not enough to claim a
statistically reliable quantization delta. The pilot does establish that the
current TinyCNN completes closed-loop tasks and that quantized behavior remains
functional. It does not establish real-robot transfer or KR260 model parity.
The teacher's 30/30 result confirms a material student-training gap under the
same task and initial-state protocol.

Machine-readable task-level results and intervals are in
[`tests/data/lite_rollout_pilot_report.json`](../../tests/data/lite_rollout_pilot_report.json).
The baseline/teacher/distillation comparison is in
[`tests/data/lite_distillation_report.json`](../../tests/data/lite_distillation_report.json).

## Decision

The preliminary decision is `tune`:

- Keep the current hardware-equivalent network as the measured baseline.
- Keep teacher action and relational visual-feature distillation; it improved
  matched FP32, PTQ, and QAT closed-loop results without changing the contract.
- Treat the remaining 20 percentage-point distilled-FP32 teacher gap as the
  optimization target; do not attribute it to quantization alone.
- Retain QAT; it recovered one matched pilot success over PTQ, but larger
  rollouts are required before attributing a reliable benefit.
- Increase closed-loop episode count after distillation and use the same fixed
  initial states for FP32/PTQ/QAT comparisons.

T014 remains `in_progress`. Final acceptance still requires the larger rollout,
recorded checkpoint/parameter artifacts, and the mandated thermo-nuclear review.

## Reproduction commands

```bash
PYTHONPATH=. .venv/bin/python tools/run_lite_gpu_evaluation.py \
  --dataset-dir data/libero/original/libero_spatial --device cuda \
  --steps 2000 --batch-size 128 --split-seed 20260921 --seed <seed>

LIBERO_CONFIG_PATH=data/libero/config \
PYTHONPATH=.:third_party/vla_adapter:data/libero/LIBERO \
data/libero/.venv/bin/python -m vla_adapter.rollout \
  --policy-kind lite --ckpt-path <checkpoint> --device cuda \
  --task-suite-name libero_spatial --num-trials-per-task 3 \
  --env-img-res 128 --num-open-loop-steps 12 \
  --mujoco-gl egl --pyopengl-platform egl

PYTHONPATH=. .venv/bin/python tools/cache_teacher_distillation.py \
  --dataset-dir data/libero/original/libero_spatial --split <train-or-validation> \
  --output-dir build/lite/t014_teacher_cache/<split> --device cuda \
  --batch-size 16 --num-workers 2

PYTHONPATH=. .venv/bin/python tools/run_lite_gpu_evaluation.py \
  --dataset-dir data/libero/original/libero_spatial --device cuda \
  --teacher-cache-dir build/lite/t014_teacher_cache \
  --resume build/lite/t014_spatial_fp32_seed20260921.pt \
  --steps 2000 --batch-size 128 --learning-rate 5e-4 \
  --action-loss-weight 1 --teacher-action-loss-weight 1 \
  --feature-loss-weight 0.1
```
