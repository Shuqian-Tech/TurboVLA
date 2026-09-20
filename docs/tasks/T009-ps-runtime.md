# T009：实现 PS DMA/AXI-Lite Runtime

- 状态：`planned`
- Sprint：Sprint 3
- 分支：`task/T009-ps-runtime`
- PR：待创建
- 依赖：T008
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务要求

实现 KR260 PS 侧 C++ runtime，负责 buffer 分配、cache flush/invalidate、DMA descriptor、AXI-Lite register、interrupt、timeout 和版本检查。PS 不得执行神经网络推理。

## 交付物

- DMA/control driver；
- buffer ownership 文档；
- 最小 CLI 或 replay runner；
- timeout/error code；
- kernel/bitstream version check。

## 详细验收（software_only；实机 bring-up deferred）

- host/replay runtime 能按 contract 提交图像、state、instruction ID 并读回 12x7 action；
- cache/coherency 测试通过；
- DMA timeout、错误 interrupt 和 reset 可恢复；
- 检查到错误 bitstream/version 时拒绝运行；
- thermo-nuclear review 确认 runtime 没有隐藏的 CPU inference fallback 或状态机 spaghetti；
- PR 附带软件日志和命令；实机日志状态为 `not_run`，直到 board-ready。
