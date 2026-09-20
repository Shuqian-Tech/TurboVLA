# T002：建立 FP32/INT8 软件 reference

- 状态：`in_review`
- Sprint：Sprint 1
- 分支：`task/T002-software-reference`
- PR：待创建（GitHub push 权限沿用 T001 阻塞）
- 依赖：T001
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T002-software-reference`
- 实现：`turbovla/lite_reference.py` 提供固定 shape 的 NumPy FP32/INT8 reference；`tools/` 下提供校准、golden 生成和逐层比较入口
- 产物：`tests/data/lite_golden/`，包含输入、逐层 FP32/INT8 tensor、量化 metadata、误差报告和 contract metadata
- 硬件 bring-up：`not_run`；KR260/JTAG 不作为软件 reference 验收前置条件

## 验证记录

- `python3 -m unittest discover -s tests -v`：通过，4 tests
- `python3 tools/validate_mvp_contract.py`：通过
- `python3 tools/generate_lite_golden.py --output-dir tests/data/lite_golden`：通过
- `python3 tools/calibrate_lite_reference.py --output tests/data/lite_calibration.json`：通过
- `python3 tools/compare_lite_reference.py tests/data/lite_golden/golden_tensors.npz tests/data/lite_golden/golden_tensors.npz`：通过，自比较误差为 0
- INT8 action 与 FP32 action：`max_abs_error=0.0007072217`，`mean_abs_error=0.0001537027`
- golden tensor SHA256：`307600ad7f29001fee8335921e9d3eaa3bceca8e6383c65252688f2f58390f28`
- `ruff check ...`：未执行，环境未安装 `ruff`
- Vivado synthesis/implementation/post-route：`not_run`；当前本地 Vivado wrapper 路径无效，T002 不宣称硬件报告通过

## Thermo-Nuclear Review

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_ENVIRONMENT_BLOCKER`
- 结构检查：reference、工具入口、测试和 golden 数据分层；核心实现 359 行，未超过 1k 行边界
- code-judo 检查：契约继续作为外部 shape/dtype/error source of truth，Lite 内部维度集中在 `LiteArchitecture`，FP32/INT8 共享输入校验和 trace 名称
- 类型/边界检查：输入 dtype/shape、instruction 越界、state 归一化、动作 shape 和 INT8 累加路径均有显式边界
- blocking findings：无代码阻塞项；`ruff` 未安装、Vivado wrapper 无效、PR 权限不足是环境/交付阻塞
- disposition：环境阻塞记录于本任务和开发状态，不通过隐式 fallback 绕过

## 任务要求

实现与硬件 shape 一致的 FP32 和 INT8 reference，包括 tiny CNN、language embedding lookup、fusion、state projection 和 action MLP。reference 必须保存逐层输出供 HLS/RTL 对齐。

## 交付物

- 固定 shape inference wrapper；
- INT8 calibration 脚本；
- golden tensors；
- 逐层误差比较工具；
- 一组可复现的输入样本。

## 详细验收

- 相同输入多次运行结果一致；
- FP32 与 INT8 的量化误差有报告；
- 误差比较能定位到具体 layer/tensor；
- 输入、输出和 metadata 与 T001 完全一致；
- thermo-nuclear review 确认 reference 没有重复的 shape/scale 分支和隐式 fallback；
- PR 包含命令、输出摘要和 golden tensor hash。
