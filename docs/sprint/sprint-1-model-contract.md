# Sprint 1：模型与硬件契约

- 状态：`in_progress`
- 目标：冻结 TurboVLA-Lite 的张量 shape、量化格式、instruction ID 接口和软件 reference
- 平台：KR260/K26，Vivado flow
- Sprint owner：Codex
- 开始时间：2026-09-19
- 结束时间：待指定

## 任务

- [T001：冻结 MVP 模型与接口契约](../tasks/T001-freeze-mvp-contract.md)
- [T002：建立 FP32/INT8 软件 reference](../tasks/T002-software-reference.md)
- [T003：训练 TurboVLA-Lite student](../tasks/T003-train-lite-student.md)
- [T004：生成 FPGA 参数包](../tasks/T004-export-fpga-parameters.md)
- [T014：GPU TinyCNN 学习能力评估](../tasks/T014-gpu-tinycnn-evaluation.md)
- [T015：升级 state INT8 scale 合同](../tasks/T015-state-scale-contract.md)

当前执行任务：[T015：升级 state INT8 scale 合同](../tasks/T015-state-scale-contract.md)

执行进度：T001 `in_review`；T002 `in_review`；T003 `in_progress`；T004 `in_progress`；T014 `in_progress`（蒸馏 FP32/PTQ/fake-QAT 为 `75/100`、`77/100`、`78/100`，teacher `95/100`，depthwise 决策 `keep_pointwise`）；T015 `in_review`（v0.3 RTL/Vivado/package gate、正确板端 `192.168.68.120` action parity 和 100-sample validation sweep 通过，等待 PR 合并，模型和权重不变）。

## 进入条件

- MVP 边界已经得到项目 owner 确认；
- KR260 是唯一目标平台；
- 已读 `AGENTS.md`、`docs/development_status.md` 和 `docs/mvp.md`。

## 退出条件

- 固定 shape 和量化格式冻结；
- FP32/INT8 reference 可重复运行；
- 当前硬件等价 TinyCNN 的 GPU 学习能力、量化损失和 LIBERO 闭环表现已测量；
- student checkpoint、instruction embedding table 和参数 metadata 已生成；
- 所有任务完成独立 PR 和 thermo-nuclear acceptance。

## Sprint 风险

- student 精度达不到目标；
- instruction ID 表无法覆盖目标任务；
- fixed-point scale 设计导致 action 误差过大。
