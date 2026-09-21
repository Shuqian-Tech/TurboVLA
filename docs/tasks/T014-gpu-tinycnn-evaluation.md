# T014：GPU TinyCNN 学习能力评估

- 状态：`in_progress`
- Sprint：Sprint 1
- 分支：`task/T014-gpu-tinycnn-evaluation`
- PR：[Shuqian-Tech/TurboVLA#3](https://github.com/Shuqian-Tech/TurboVLA/pull/3)（Draft）
- 依赖：T001、T002、T003 训练骨架
- 后续任务：T003 正式训练闭环、T004 正式参数包、T012 最终发布验收
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务动机

在投入正式 FPGA 参数固化和发布验证前，先在 CUDA GPU 上测量当前硬件等价
TinyCNN student 的可学习上限。评估必须区分模型容量、训练流程、量化和数据覆盖
造成的误差，给后续“保持结构、有限扩容或重新设计视觉 encoder”提供量化依据。

本任务是训练和评测任务，不改变唯一部署目标 AMD Kria KR260/K26。GPU 只用于
离线训练、蒸馏和评测；不得引入 GPU、DPU 或 CPU runtime inference fallback。

## 当前环境基线

- GPU：NVIDIA GeForce RTX 3070，8192 MiB
- 驱动：595.84
- PyTorch：2.14.0+cu130
- CUDA runtime：13.0
- `torch.cuda.is_available()`：`True`
- 当前 student：固定 128x128 单视角、32 visual tokens、hidden 128、两层 gated fusion、12x7 action，共 148436 参数
- 当前缺口：teacher action/feature 蒸馏和扩大闭环 episode 数尚未完成；当前 3 episodes/task 仅作为 pilot

## 当前执行记录

- 开始时间：2026-09-21
- 当前阶段：无 teacher 行为克隆基线、FP32/PTQ/QAT 离线与闭环 pilot 已完成
- 数据策略：官方 `libero_spatial` 10-task HDF5，按 demo 固定划分，流式生成固定 128x128 单视角训练样本
- 硬件部署边界：本任务不修改 KR260 bitstream、PL runtime 或 PS/PL 分工

## 2026-09-21 Pilot 证据

- LIBERO source commit：`8f1084e3132a39270c3a13ebe37270a43ece2a01`
- HDF5 revision：`e329580e402fb5f07ae3b1f18475fc3b63783b91`
- 固定 split seed：`20260921`；train 51,109，validation 11,044
- 3-seed FP32 validation MAE：`0.127903 +/- 0.000432`（population std）
- 3-seed gripper sign accuracy：`0.925218 +/- 0.001191`
- seed 20260921 离线 FP32/PTQ/QAT MAE：`0.127495 / 0.130040 / 0.128612`
- 30-episode matched closed-loop pilot：FP32 `22/30`，PTQ `18/30`，QAT `19/30`
- FP32 Wilson 95% interval：`[0.5555, 0.8582]`；量化区间与其重叠，暂不宣称显著差异
- 当前数据只使用 ground-truth demonstration action；teacher action/feature 蒸馏尚未开始
- 初步决策：`tune`，先做蒸馏与训练策略调整，不立即修改 FPGA 模型合同
- 完整说明：[`docs/evaluation/t014_gpu_tinycnn_pilot.md`](../evaluation/t014_gpu_tinycnn_pilot.md)
- 机器可读报告：`tests/data/lite_gpu_evaluation_report.json`、`tests/data/lite_rollout_pilot_report.json`

## 当前验证记录

- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：22 tests 通过
- changed-file `ruff check`：通过；仓库全量 ruff 仍有 30 个与本任务无关的既有 finding
- CUDA checkpoint load：通过，无 CPU fallback
- LIBERO EGL offscreen rollout：通过，10/10 tasks 均产生明确 episode 分母
- PTQ checkpoint SHA256：`65ff8cb5de0f294772af8dc0b5ba48d2df8ac7aa91b92da41c91323ff3bfe9af`

## 剩余 gate

- 接入 teacher action 与 visual feature 蒸馏，并记录 teacher/student 同协议对照
- 扩大闭环 episode 数，缩窄总体和逐任务置信区间
- 从最终 QAT checkpoint 生成 T004 参数包并执行软件/PL parity
- 完成 `thermo-nuclear-code-quality-review` 后才能进入 `in_review`

## 任务范围

1. 为训练和评测入口增加显式 `--device cuda`；请求 CUDA 时不可用必须立即失败，禁止静默退回 CPU。
2. 保持 FPGA 合同的输入、输出、算子和 shape 不变，先训练当前精确硬件等价结构。
3. 分别运行 FP32、fake-quant/QAT 和导出后硬件兼容 INT8 评估，拆分容量误差与量化误差。
4. 使用固定 train/validation split、至少 3 个随机种子和可恢复 checkpoint，记录均值、标准差及最差 seed。
5. 执行小数据集过拟合诊断、held-out 离线评估和 LIBERO 闭环 rollout 三层测试。
6. 如果精确结构表现不足，只允许进行预先记录的 FPGA 友好小范围容量 sweep；不得在本任务内修改 RTL、Vivado block design 或部署合同。

## 对照与指标

- teacher、ground-truth action、FP32 student、QAT student 和硬件兼容 INT8 使用同一数据划分与 rollout protocol。
- 小样本过拟合：用于判断实现或优化器是否存在基础问题，不作为泛化成绩。
- 离线指标：action L1/MAE、最大绝对误差、teacher-action L1、visual feature MSE，并按 instruction/task 分桶。
- 闭环指标：LIBERO 每任务成功次数、总 episode 数、成功率、相对 teacher/FP32 降幅和置信区间。
- 训练指标：loss curve、验证曲线、吞吐、峰值显存、训练时长、checkpoint SHA256 和数据版本。
- 量化指标：FP32 -> QAT -> INT8 的逐阶段误差与成功率变化，禁止只报告最终最好结果。

## 决策输出

评估报告必须给出一个有证据支持的结论：

- `keep`：当前精确结构具备进入正式 T003/T004 的能力；
- `tune`：结构可用，但训练、蒸馏、数据或量化策略需要调整；
- `redesign`：在通过过拟合诊断和合理 sweep 后，容量仍明显不足，需要先更新模型合同。

本任务的验收依据是评估完整、可复现且结论可信，不以达到某个预设成功率作为
完成条件。正式模型进入发布前的最低成功率和允许降幅仍须由项目 owner 在正式训练
开始前批准。

## 交付物

- CUDA-aware TinyCNN 训练入口和单元测试；
- 可复现的数据 split、seed 和实验配置；
- FP32、QAT、INT8 checkpoint/manifest 及 checksum；
- 离线指标、学习曲线和 GPU 利用情况报告；
- LIBERO rollout 原始结果和汇总报告；
- `keep`、`tune` 或 `redesign` 决策记录。

## 详细验收

- 精确硬件等价结构必须先于任何容量 sweep 完成评估；
- CUDA 请求不可静默回退，报告记录 GPU、驱动、PyTorch/CUDA、峰值显存和命令；
- train/validation 数据无样本泄漏，split 和数据版本可追溯；
- 至少 3 个 seed 使用相同预算运行，并报告全部结果而非挑选最佳 seed；
- FP32、QAT、INT8 使用一致输入和评测协议，可定位量化造成的独立损失；
- LIBERO 闭环结果包含每任务 episode 分母和失败分布；
- 不引入 GPU/DPU/CPU 部署路径，PS/PL 边界保持不变；
- thermo-nuclear review 覆盖数据边界、配置复杂度、重复训练逻辑、文件大小和决策证据；
- PR 附带命令、日志、报告、checkpoint hash，以及每个 finding 的 disposition。
