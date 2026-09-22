# Tasks 记录

用于保存 TurboVLA 纯 FPGA/KR260 项目的具体任务、验收标准、依赖关系和完成状态。

## 任务规则

- 每个任务必须是一个独立 Markdown 文件；
- 每个任务必须使用独立分支并创建独立 PR；
- 每个任务必须记录状态、分支、PR、依赖、交付物、验证命令和验收证据；
- 每个任务验收必须执行 `thermo-nuclear-code-quality-review` skill；
- 任务状态以任务文件和 [开发状态](../development_status.md) 为准。

## 任务索引

### Sprint 1

- [T001：冻结 MVP 模型与接口契约](T001-freeze-mvp-contract.md)
- [T002：建立 FP32/INT8 软件 reference](T002-software-reference.md)
- [T003：训练 TurboVLA-Lite student](T003-train-lite-student.md)
- [T004：生成 FPGA 参数包](T004-export-fpga-parameters.md)
- [T014：GPU TinyCNN 学习能力评估](T014-gpu-tinycnn-evaluation.md)
- [T015：升级 state INT8 scale 合同](T015-state-scale-contract.md)

### Sprint 2

- [T005：实现 INT8 GEMM/Conv IP](T005-gemm-conv-ip.md)
- [T006：实现 Fusion 与 Action MLP IP](T006-fusion-action-ip.md)
- [T007：搭建 KR260 Vivado Block Design](T007-kr260-block-design.md)
- [T008：完成综合、布局布线和报告基线](T008-vivado-baseline.md)

### Sprint 3

- [T009：实现 PS DMA/AXI-Lite Runtime](T009-ps-runtime.md)
- [T010：实现数据回放与数值对齐测试](T010-replay-validation.md)
- [T011：完成机器人闭环与稳定性测试](T011-closed-loop-stability.md)
- [T012：最终 thermo-nuclear 审查与发布归档](T012-final-acceptance.md)
