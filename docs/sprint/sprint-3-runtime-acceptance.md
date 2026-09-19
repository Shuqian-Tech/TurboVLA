# Sprint 3：Runtime、闭环与发布验收

- 状态：`planned`
- 目标：在 KR260 实机上完成无 CPU inference fallback 的 action 输出、回放和闭环验收
- 平台：KR260/K26，Vivado bitstream + PS runtime
- Sprint owner：待指定
- 开始时间：待指定
- 结束时间：待指定

## 任务

- [T009：实现 PS DMA/AXI-Lite Runtime](../tasks/T009-ps-runtime.md)
- [T010：实现数据回放与数值对齐测试](../tasks/T010-replay-validation.md)
- [T011：完成机器人闭环与稳定性测试](../tasks/T011-closed-loop-stability.md)
- [T012：最终 thermo-nuclear 审查与发布归档](../tasks/T012-final-acceptance.md)

## 进入条件

- Sprint 2 bitstream 已通过 post-route timing；
- XSA、kernel 参数包、寄存器表和版本号已冻结；
- KR260 实机和 PS runtime 环境可用。

## 退出条件

- DMA 输入和 `12x7` action 输出稳定；
- replay、数值、延迟、DDR 带宽和功耗报告齐全；
- 连续 30 分钟无 DMA、NaN、超时或动作漂移；
- 所有任务独立 PR 合并；
- T012 通过 thermo-nuclear skill 并更新最终开发状态。

## Sprint 风险

- PS cache/coherency 导致数据不一致；
- 实机时序和仿真不一致；
- robot safety layer 未覆盖超时、限幅和急停路径。
