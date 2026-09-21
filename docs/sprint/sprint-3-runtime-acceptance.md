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
- [T013：补齐 PL 推理链、PS Runtime 与端到端数值对齐](../tasks/T013-pl-runtime-e2e.md)

当前执行任务：[T013：补齐 PL 推理链、PS Runtime 与端到端数值对齐](../tasks/T013-pl-runtime-e2e.md)

执行进度：T009 `in_progress`（host/replay register/DMA model 已通过）；T010 `in_progress`（golden replay 和逐层报告已通过）；T011 `in_progress`（1000-cycle safety replay 已通过）；T012 `in_progress`（Draft PR #1、发布 manifest、分阶段 gated-fusion co-sim 和 board probe 记录已生成）；T013 `in_review`（200 MHz Vivado backend、bitstream/XSA、exact-commit RTL co-sim、KR260 package load、自动 PL0 clock enable、JTAG AXI-Lite read、runtime probe、84-value PL action parity、17,019-iteration/30-minute board stability 和最终 thermo-nuclear review 均通过；PR #2 待 review/merge）。T013 高内存构建固定从 GitHub branch revision 在 `frank@192.168.68.119:/home/frank/TurboVLA-codex-T013` 隔离 worktree 执行。项目 owner 于 2026-09-21 将首版上板的 WNS/TNS 改为 reporting-only；本次最终 post-route WNS 实际为 `+0.002 ns`、TNS `0`。追加 live load capture 为 12/12 次成功，`Temp_PL` 29.003-31.396 C、board power 3.350-3.440 W。

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
