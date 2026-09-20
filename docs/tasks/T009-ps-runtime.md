# T009：实现 PS DMA/AXI-Lite Runtime

- 状态：`in_progress`
- Sprint：Sprint 3
- 分支：`task/T009-ps-runtime`
- PR：待创建
- 依赖：T008
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T009-ps-runtime`
- runtime：`runtime/include/turbovla_runtime.hpp`、`runtime/src/turbovla_runtime.cpp`
- host/replay testbench：`runtime/src/tb_runtime.cpp`、`tools/run_runtime_csim.py`
- PL 边界：runtime 只提交固定输入并等待显式 `PlExecutor`；没有 CPU inference fallback
- 硬件 bring-up：`not_run`

## 验证记录

- `python3 tools/run_runtime_csim.py`：通过，register/DMA model、version mismatch、invalid instruction 和 timeout 均覆盖
- 编译参数：`g++ -std=c++17 -O2 -Wall -Wextra -Werror`
- `ruff check tools/run_runtime_csim.py`：通过
- 实机 DMA/cache/interrupt：`not_run`；当前为 host/replay software-only model

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_REPLAY_GATE`
- 结构检查：register model、runtime state 和 testbench 分离；错误码直接复用 T001 contract
- code-judo 检查：PL 执行通过单一 `PlExecutor` 边界注入，避免在 runtime 内复制模型或增加 fallback 分支
- blocking findings：无代码 blocking finding；真实 DMA/cache/interrupt 设备日志尚未提供
- disposition：保留 `in_progress`，待 T010 replay 和后续 board-ready bring-up

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
