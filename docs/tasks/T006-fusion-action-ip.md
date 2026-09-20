# T006：实现 Fusion 与 Action MLP IP

- 状态：`in_progress`
- Sprint：Sprint 2
- 分支：`task/T006-fusion-action-ip`
- PR：待创建
- 依赖：T005
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T006-fusion-action-ip`
- kernel：`hardware/hls/fusion_action/fusion_action.{h,cpp}`
- 覆盖：32x128 visual tokens、128-dim language token、8-dim state、12x7 action
- 非线性：hard-sigmoid + bounded tanh，避免 softmax 和动态分支
- 构建入口：`tools/run_fusion_action_csim.py`
- 硬件 bring-up：`not_run`

## 验证记录

- `python3 tools/run_fusion_action_csim.py`：通过，输出 `fusion/action C simulation passed`
- 编译参数：`g++ -std=c++17 -O2 -Wall -Wextra -Werror`
- `ruff check hardware/hls/fusion_action tools/run_fusion_action_csim.py`：通过
- HLS co-simulation、synthesis、resource/latency report：`not_run`，Vivado/HLS 工具路径无效
- action output shape：固定 `12x7`

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_TOOLCHAIN_GATE`
- 结构检查：fusion 负责 gated mixing，action MLP 只负责 state/pool/projection；GEMM 由 T005 统一复用
- code-judo 检查：没有引入 attention/softmax 模式开关；固定 shape 和 hard nonlinearity 保持单一路径
- blocking findings：无代码 blocking finding；缺少 HLS/Vivado 报告和 T002 数值逐层对齐
- disposition：保留 `in_progress`，待工具链恢复后补齐综合和误差报告

## 任务要求

实现 language embedding 与 visual tokens 的 gated fusion 或固定 shape cross-attention，并实现 state projection、12x7 action MLP。第一版优先使用 gated fusion；只有资源和时序允许时才启用 softmax attention。

## 交付物

- fusion IP；
- action MLP IP；
- fixed-point nonlinearity implementation；
- 逐层 RTL/HLS 与 reference 对齐报告。

## 详细验收

- visual token、language token 和 state token 的 shape 与 T001 一致；
- action 输出为固定的 12x7；
- quantization error 在 T002 阈值内；
- softmax 被禁用时不存在未定义的 fallback path；
- thermo-nuclear review 确认 gated/cross-attention 模式没有扩散到全局代码的条件分支；
- PR 包含 kernel latency、资源和误差报告。
