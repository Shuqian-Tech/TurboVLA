# T010：实现数据回放与数值对齐测试

- 状态：`in_progress`
- Sprint：Sprint 3
- 分支：`task/T010-replay-validation`
- PR：待创建
- 依赖：T009
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T010-replay-validation`
- replay runner：`tools/run_lite_replay.py`
- 输入 bundle：`tests/data/lite_golden/golden_tensors.npz`
- 输出报告：`tests/data/lite_replay_report.json`
- verification mode：`software_only`；hardware bring-up：`not_run`

## 验证记录

- `PYTHONPATH=. .venv/bin/python tools/run_lite_replay.py --bundle tests/data/lite_golden/golden_tensors.npz --output tests/data/lite_replay_report.json --repeats 10`：通过
- FP32/INT8 每层 shape 与 golden：通过
- INT8 action replay：`max_abs_error=0.0`，`mean_abs_error=0.0`
- software-only latency（本次报告）：FP32 p50/p99 `0.9591/1.8882 ms`；INT8 p50/p99 `5.3749/7.9713 ms`
- `ruff check tools/run_lite_replay.py`：通过
- HLS/RTL/Vivado target replay 和实机回放：`not_run`

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_HARDWARE_GATE`
- 结构检查：bundle loader、逐层 comparator、latency recorder 和 report writer 在一个无隐式状态的 replay flow 中完成
- code-judo 检查：FP32/INT8 通过同一 `replay_bundle` 路径分派，不复制 golden parser 或手工修正输出
- blocking findings：无代码 blocking finding；硬件 kernel/Vivado replay 尚未可运行
- disposition：保留 `in_progress`，待 T005-T008 工具链和真实 PL capture 接入

## 任务要求

建立从 Python golden tensors 到 KR260 目标软件工程的 deterministic replay，比较每层或每个 kernel 的输出、最终 action、延迟和 DDR 带宽；实机回放延后到 board-ready。

## 交付物

- replay input bundle；
- host/reference comparator；
- FPGA output capture；
- 数值和性能报告。

## 详细验收

- 同一个输入 bundle 在软件 reference、HLS/RTL co-simulation 和 Vivado 生成的目标工程中可重复运行；
- 每个 kernel 的误差定位到 tensor/layer；
- action MAE、最大误差和 latency p50/p99 自动生成；
- 不允许手工修改输出或跳过失败样本；
- thermo-nuclear review 确认测试编排没有重复解析器和隐式状态；
- PR 附带失败样本处理规则和报告。
- 实机回放状态明确记录为 `not_run`，不将 software-only 输出写成 KR260 实机结果。
