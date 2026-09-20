# Sprint 3：Runtime、闭环与发布验收

- 状态：`in_progress`
- 目标：先完成无 CPU inference fallback 的软件 runtime、回放和 Vivado 证据归档；实机闭环作为 board-ready 后的追加 gate
- 平台：KR260/K26，Vivado bitstream + PS runtime
- Sprint owner：Codex
- 开始时间：2026-09-19
- 结束时间：待指定

## 任务

- [T009：实现 PS DMA/AXI-Lite Runtime](../tasks/T009-ps-runtime.md)
- [T010：实现数据回放与数值对齐测试](../tasks/T010-replay-validation.md)
- [T011：完成机器人闭环与稳定性测试](../tasks/T011-closed-loop-stability.md)
- [T012：最终 thermo-nuclear 审查与发布归档](../tasks/T012-final-acceptance.md)

当前执行任务：[T012：最终 thermo-nuclear 审查与发布归档](../tasks/T012-final-acceptance.md)

执行进度：T009 `in_progress`（host/replay register/DMA model 已通过）；T010 `in_progress`（golden replay 和逐层报告已通过）；T011 `in_progress`（1000-cycle safety replay 已通过）；T012 `in_progress`（发布 manifest 和审查报告已生成）。Sprint 2 旧 Vivado baseline 已通过；当前 `tanh_q15` 修正后的全量重建待另一台机器执行。

## 进入条件

- Sprint 2 bitstream 已通过 post-route timing；
- XSA、kernel 参数包、寄存器表和版本号已冻结；
- PS runtime 可以在 host/replay 环境构建；KR260 实机不可用时，硬件 bring-up 状态为 `not_run`。

## 退出条件

- 软件 DMA/register model、replay 和 `12x7` action 输出稳定；
- replay、数值、延迟、DDR 带宽和功耗报告齐全；
- 软件 replay 连续运行无 DMA model、NaN 或超时错误；实机 30 分钟稳定性推迟到 board-ready 后；
- 所有任务独立 PR 合并；
- T012 通过 thermo-nuclear skill 并更新最终开发状态。

## Sprint 风险

- PS cache/coherency 导致数据不一致；
- 实机时序和仿真不一致（board-ready 后处理）；
- robot safety layer 未覆盖超时、限幅和急停路径。
