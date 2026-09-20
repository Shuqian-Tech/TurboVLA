# Sprint 2：PL Kernel 与 Vivado Block Design

- 状态：`in_progress`
- 目标：完成可综合的 kernel、KR260 block design 和第一次 software-only post-route timing baseline
- 平台：KR260/K26，Vivado flow
- Sprint owner：Codex
- 开始时间：2026-09-19
- 结束时间：待指定

## 任务

- [T005：实现 INT8 GEMM/Conv IP](../tasks/T005-gemm-conv-ip.md)
- [T006：实现 Fusion 与 Action MLP IP](../tasks/T006-fusion-action-ip.md)
- [T007：搭建 KR260 Vivado Block Design](../tasks/T007-kr260-block-design.md)
- [T008：完成综合、布局布线和报告基线](../tasks/T008-vivado-baseline.md)

当前执行任务：[T008：完成综合、布局布线和报告基线](../tasks/T008-vivado-baseline.md)

执行进度：T005 `in_review`（GEMM/Conv HLS synthesis、IP export、RTL co-sim 通过）；T006 `in_review`（fusion/action C simulation 与 synthesis/IP export 通过，action RTL co-sim 通过，gated-fusion RTL co-sim deferred）；T007/T008 `in_progress`（旧 Vivado baseline 通过，但当前 `tanh_q15` 修正后的全量重建待另一台机器执行）；Sprint 1 T001-T004 的 PR/正式训练门仍未闭合。

## 进入条件

- Sprint 1 的参数包和 reference 已被接受；
- 所有 tensor layout、scale、stride 和 buffer ownership 已冻结；
- kernel 不允许使用 CPU fallback。

## 退出条件

- C simulation、HLS co-simulation 和 RTL/FPGA 输出可对齐；
- PS、DDR、AXI DMA、AXI-Lite scheduler 和 PL kernel 已连通；
- software Vivado post-route timing 无 violation，资源和功耗报告已保存；
- 硬件板/JTAG 状态记录为 `not_run`，不影响 Sprint 2 软件退出；
- 每个任务独立 PR 通过 thermo-nuclear acceptance。

## Sprint 风险

- unroll/partition 导致 DSP、BRAM 或 routing congestion 超限；
- DDR 带宽不能支撑 activation/weight 流；
- attention 实现的软最大值或归一化造成误差/时序问题。
