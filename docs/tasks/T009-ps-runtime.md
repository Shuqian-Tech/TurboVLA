# T009：实现 PS DMA/AXI-Lite Runtime

- 状态：`done`
- Sprint：Sprint 3
- 分支：`task/T009-ps-runtime`
- PR：[Shuqian-Tech/TurboVLA#9](https://github.com/Shuqian-Tech/TurboVLA/pull/9)（merged，commit `737e9645322df219494eb12d9e1ef4813cd12db9`）
- 依赖：T008
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T009-ps-runtime`
- runtime：`runtime/include/turbovla_runtime.hpp`、`runtime/src/turbovla_runtime.cpp`、`runtime/src/turbovla_board.cpp`
- host/replay testbench：`runtime/src/tb_runtime.cpp`、`tools/run_runtime_csim.py`
- PL 边界：runtime 只提交固定输入并等待显式 `PlExecutor`；没有 CPU inference fallback
- buffer ownership：`runtime/README.md`
- 硬件 bring-up：`passed`；精确 source commit `281d7d45c42a09eaba902c1da436a063800f7b12`

## 验证记录

- `python3 tools/run_runtime_csim.py`：通过；cache/MMIO、TOW interrupt、timeout recovery、invalid model replacement、unknown error、non-finite action 和 instruction bounds 均覆盖
- 编译参数：`g++ -std=c++17 -O2 -Wall -Wextra -Werror`
- ASan/UBSan C++ testbench：通过
- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：35 tests 通过
- contract/register validators 和 scoped ruff：通过
- KR260 `.120`：精确提交独立 worktree 构建；5/5 validation fixtures 通过，84-value worst max absolute error `8.94070e-08`，mean runtime call latency `76.087 ms`
- 实机 interrupt：每次捕获 completion ISR `0x1`，返回前 `GIE/IER/ISR=0/0/0`；FPGA manager 最终为 `operating`
- 证据：[T009 KR260 runtime bring-up](../../hardware/vivado_kr260/reports/t009_runtime_bringup.md)

## Thermo-Nuclear Review（最终）

- review 时间：2026-09-22
- reviewer：Codex
- review 范围：PR #9，`origin/main...b6f4412`，245 additions / 14 deletions（状态文档提交前）
- review 结果：`PASS`；无未处置 blocking finding
- 结构/code-judo：单一 aligned arena、`RegisterIo`、`CacheMaintenance` 和 `PlArenaExecutor` 保持 transport/control 边界；未添加 DMA descriptor 层、第二状态机或 CPU inference fallback
- 文件大小：runtime 源文件最大 288 行；PR 未使任何文件接近或超过 1,000 行
- 抽象/分支：恢复逻辑集中在 `reset_control()`；错误码 decode、header/version/sequence/action 检查在 executor canonical boundary，无 platform-specific 条件链
- boundary：唯一目标仍为 KR260/K26；无 DPU、Vitis AI、GPU runtime 或替代 FPGA preset
- finding 1：最初把 HLS ISR 当作 W1C 并写全 1；实际生成 RTL 为 Read/TOW。已改成 read-mask-write，并由真实 ISR 和 fake MMIO 测试覆盖
- finding 2：成功返回后 completion ISR 曾保持 pending。已改成捕获诊断值后关闭 GIE/IER 并 acknowledge；板端 5/5 均观察 `ISR=1` 且最终寄存器清零
- finding 3：有效模型后尝试加载无效模型会保留旧 `model_loaded_`。已改成每次 load 先撤销状态，并覆盖 reject/reload recovery
- disposition：所有 finding 已解决；真实板端故障注入因非破坏性边界未运行，timeout/error/reset-control 使用 fake MMIO 验证，不宣称平台级 PL reset

## 任务要求

实现 KR260 PS 侧 C++ runtime，负责 buffer 分配、cache flush/invalidate、DMA descriptor、AXI-Lite register、interrupt、timeout 和版本检查。PS 不得执行神经网络推理。

## 交付物

- DMA/control driver；
- buffer ownership 文档；
- 最小 CLI 或 replay runner；
- timeout/error code；
- kernel/bitstream version check。

## 详细验收

- host/replay runtime 能按 contract 提交图像、state、instruction ID 并读回 12x7 action；
- cache/coherency 测试通过；
- DMA timeout、错误 interrupt 和 reset 可恢复；
- 检查到错误 bitstream/version 时拒绝运行；
- thermo-nuclear review 确认 runtime 没有隐藏的 CPU inference fallback 或状态机 spaghetti；
- PR 附带软件和实机命令、精确 commit、binary checksum、fixture 结果及边界说明。
