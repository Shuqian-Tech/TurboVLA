# T014：GPU TinyCNN 学习能力评估

- 状态：`done`
- Sprint：Sprint 1
- 分支：`task/T014-gpu-tinycnn-evaluation`
- PR：[Shuqian-Tech/TurboVLA#3](https://github.com/Shuqian-Tech/TurboVLA/pull/3)（merged，待本次收尾合并）
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
- 当前缺口：最终 FPGA 参数包和强制 code-quality review 尚未完成；10 episodes/task 扩大评测已完成

## 当前执行记录

- 开始时间：2026-09-21
- 当前阶段：行为克隆 baseline、teacher action/feature 蒸馏、100-episode 扩大评测和 depthwise 容量消融已完成
- 数据策略：官方 `libero_spatial` 10-task HDF5，按 demo 固定划分，流式生成固定 128x128 单视角训练样本
- 硬件部署边界：本任务不修改 KR260 bitstream、PL runtime 或 PS/PL 分工

## 2026-09-21 Pilot 证据

- LIBERO source commit：`8f1084e3132a39270c3a13ebe37270a43ece2a01`
- HDF5 revision：`e329580e402fb5f07ae3b1f18475fc3b63783b91`
- TurboVLA teacher revision：`cb5300544693013164c4bb251a13036002a55c81`
- Teacher checkpoint SHA256：`d031ad7be05a2f5d04afb3194ed26b0cb46083685edee7a5e145078a37d26bab`
- 固定 split seed：`20260921`；train 51,109，validation 11,044
- 3-seed FP32 validation MAE：`0.127903 +/- 0.000432`（population std）
- 3-seed gripper sign accuracy：`0.925218 +/- 0.001191`
- seed 20260921 离线 FP32/PTQ/QAT MAE：`0.127495 / 0.130040 / 0.128612`
- 30-episode matched closed-loop pilot：FP32 `22/30`，PTQ `18/30`，QAT `19/30`
- 同协议 TurboVLA teacher：`30/30`；相对 FP32 TinyCNN 高 26.67 percentage points
- FP32 Wilson 95% interval：`[0.5555, 0.8582]`；量化区间与其重叠，暂不宣称显著差异
- baseline 只使用 ground-truth demonstration action；后续 teacher action/feature 蒸馏结果见下节
- 初步决策：`tune`，先做蒸馏与训练策略调整，不立即修改 FPGA 模型合同
- 完整说明：[`docs/evaluation/t014_gpu_tinycnn_pilot.md`](../evaluation/t014_gpu_tinycnn_pilot.md)
- 机器可读报告：`tests/data/lite_gpu_evaluation_report.json`、`tests/data/lite_rollout_pilot_report.json`

## 当前验证记录

- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：30 tests 通过
- changed-file `ruff check`：通过；仓库全量 ruff 仍有 30 个与本任务无关的既有 finding
- CUDA checkpoint load：通过，无 CPU fallback
- LIBERO EGL offscreen rollout：通过，10/10 tasks 均产生明确 episode 分母
- 官方 teacher 严格加载：672/672 tensors，216,073,239 parameters，BF16 CUDA rollout `30/30`
- 官方 checkpoint loader 同时支持 `ema_model_state_dict` 和 release 使用的 `model_state_dict`
- PTQ checkpoint SHA256：`65ff8cb5de0f294772af8dc0b5ba48d2df8ac7aa91b92da41c91323ff3bfe9af`
- depthwise FP32 热启动、校准、PTQ checkpoint 和 1-step QAT smoke：通过；当前 FPGA 参数包导出拒绝实验 encoder

## 2026-09-21 Distillation Pilot

- teacher cache：51,109 train + 11,044 validation；teacher BF16 action 与主视角 task-conditioned token relation 均使用 FP16 持久化
- feature target：teacher 主视角 post-language-fusion `16x16` token 自适应池化到 `4x8`，再计算 channel-independent `32x32` cosine relation；学生使用 `fusion_1` 对齐，不新增部署参数
- cache index SHA256：train `571ad7ddc4dcc307779aaec3c9b75492fc2acb6d37653d6b1c20ec6767a7df98`；validation `c059e5112e3ddef6fe9b124382f0efd0ebb66bf39244e187cbd8e28fdea3441e`
- cache tensor SHA256：train action/relation `3637e30db0906204caaa0e0c314160f4fb33b39ffd45805b51e3385846b29547 / f5a6c9a2d1c85c07292fde517783605ba63ec536dbdfd842b7ed3eca4157f024`；validation action/relation `5220641e8441be5653a371ebed83df3eb9b9e35364a1afb5059de461545038c3 / 0c9f45fa64a5232ed4f7eee7b03552e78dd8f078dfe3c7d4a29ef5cbf16efac8`
- distillation loss：ground-truth action : teacher action : relation = `1.0 : 1.0 : 0.1`
- FP32 validation：action MAE `0.127495 -> 0.126056`；teacher-action MAE `0.103029 -> 0.077485`；feature relation MSE `0.011283 -> 0.005770`
- distilled FP32 checkpoint SHA256：`dce6da5c26a4f06e5121ab7e0efee88cfc459c0aacfc9633e00c9c3ecde4a03a`
- distilled PTQ/QAT validation MAE：`0.130382 / 0.128996`
- distilled PTQ/QAT checkpoint SHA256：`38f783732d01272b8b5a7831ef82afebb03e86229524061079fca8eb01fc9a97 / 7209a40065aa72628bd1a2b3b92d92a205ac97a4bb1a4577c1e4eda3d5d5dc1a`
- matched 30-episode baseline FP32/PTQ/QAT：`22/30 / 18/30 / 19/30`
- matched 30-episode distilled FP32/PTQ/QAT：`24/30 / 22/30 / 23/30`
- teacher：`30/30`；蒸馏将 FP32 teacher gap 从 8 个回合缩到 6 个，QAT 相对 distilled FP32 仅少 1 个回合
- 机器可读报告：`tests/data/lite_distillation_report.json`

## 2026-09-21 Expanded Closed-loop Evidence

- 协议：`libero_spatial` 全 10 tasks，每任务前 10 个固定 initial states，seed 7，每次预测执行 12 个 open-loop actions
- distilled FP32：`75/100`，Wilson 95% interval `[65.70%, 82.45%]`
- distilled PTQ fake INT8：`77/100`，Wilson 95% interval `[67.85%, 84.16%]`，相对 FP32 `+2 pp`
- distilled QAT fake INT8：`78/100`，Wilson 95% interval `[68.93%, 85.00%]`，相对 FP32 `+3 pp`
- TurboVLA teacher BF16：`95/100`，Wilson 95% interval `[88.82%, 97.85%]`，相对 FP32 `+20 pp`
- 三个 student 区间高度重叠；当前证据不支持 PTQ/QAT 优于 FP32，只支持“未观察到总体量化退化”
- student 的主要失败集中在 task 8/9：FP32 均为 `4/10`；task 8 的 PTQ/QAT 均为 `4/10`，task 9 均为 `5/10`；teacher 为 `9/10`、`10/10`
- 机器可读报告：`tests/data/lite_distillation_expanded_report.json`
- 决策保持 `tune`：CUDA depthwise 消融结果见下节；未达到更新 HLS/硬件合同的收益门槛

## 2026-09-21 Depthwise Capacity Ablation

- 候选结构：保留原 `1x1` stem，在 `16x16` 中间特征上增加两个残差式 `3x3 depthwise + 1x1 pointwise` block，再池化回固定 `4x8` tokens
- 默认 pointwise 参数量保持 `148436`；depthwise 候选为 `149300`，增加 864 个参数
- 候选 pointwise projection 零初始化；从蒸馏 FP32 checkpoint 热启动时，初始 action 与默认结构数值误差不超过 `2e-6`
- 严格匹配 continuation control：两组都从同一蒸馏 FP32 checkpoint 开始，使用相同 seed、teacher cache、batch 128、学习率 `5e-4` 和 2,000 update steps
- pointwise/depthwise validation action MAE：`0.12505893 / 0.12505184`；差值仅 `0.00000709`
- pointwise/depthwise teacher-action MAE：`0.07460589 / 0.07460894`
- pointwise/depthwise feature relation MSE：`0.00507810 / 0.00490191`；depthwise 改善约 3.5%，但未转化为动作收益
- matched task 8/9 rollout：两者均为 task 8 `5/10`、task 9 `4/10`，总计 `9/20`
- checkpoint SHA256：pointwise control `e28084f0ea4b5abae6352a43a89443ff4a6bdf14de3bc3b3824f87e6fc04b059`；depthwise `c02d1118e2ce933ceccf6d1151d10c616bec0522bc377fe1b67fedd0dac5135f`
- 机器可读闭环报告：`tests/data/lite_depthwise_ablation_report.json`
- 决策：`keep_pointwise`。不为该候选运行完整 100 episodes，不更新 FPGA 合同；实验 checkpoint 的参数包导出会 fail-fast

## 最终验收

- 最终选定 checkpoint：QAT SHA256 `7209a40065aa72628bd1a2b3b92d92a205ac97a4bb1a4577c1e4eda3d5d5dc1a`；T015 在不改变模型和权重的前提下完成 v0.3 state-scale ABI、正式参数包和软件/PL parity。
- T004/T015 正式参数包：19 tensors，`model.bin` 150656 bytes，SHA256 `6df32b27eb8a730027c6f37af8c8bd33058700293941a44eae6ade0697fa3886`；exact INT8/HLS/RTL action parity、Vivado 全量构建和 KR260 `.120` action parity 已通过。
- thermo-nuclear review：2026-09-22，reviewer Codex，结果 `PASS_WITH_DEVICE_AND_PR_GATES`；无结构或代码 blocking finding。审查覆盖文件大小、抽象边界、分支复杂度、数据/训练配置边界、CUDA-only 离线评估和 PL-only 部署边界；所有 finding 已处置。
- PR #3 在上述证据完整后转 Ready 并合并；T014 不修改 FPGA 模型合同，决策为 `keep_pointwise`，评估结论为 `tune`。

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
