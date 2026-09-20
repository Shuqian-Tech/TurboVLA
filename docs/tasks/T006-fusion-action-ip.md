# T006：实现 Fusion 与 Action MLP IP

- 状态：`in_review`
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
- `TURBOVLA_LOCALE_ROOT=/tmp/turbovla-repo-locale tools/run_vitis_hls.sh hardware/hls/fusion_action/vitis_hls.tcl`：通过，Vitis HLS C simulation 输出 `fusion/action C simulation passed`
- `TURBOVLA_HLS_SYNTH=1 tools/run_vitis_hls.sh hardware/hls/fusion_action/vitis_hls.tcl`：fusion/action synthesis、IP export 通过
- action MLP RTL co-simulation：`COSIM 212-1000 PASS`；gated-fusion RTL co-sim deferred because the XSIM wrapper grows without bounded completion, not claimed as pass
- Vivado system synthesis/implementation/post-route：归档 baseline 通过；`tanh_q15` 修正后的系统重建待另一台机器执行
- action output shape：固定 `12x7`

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_COSIM_GATE`
- 结构检查：fusion 负责 gated mixing，action MLP 只负责 state/pool/projection；GEMM 由 T005 统一复用
- code-judo 检查：没有引入 attention/softmax 模式开关；固定 shape 和 hard nonlinearity 保持单一路径
- blocking findings：无代码 blocking finding；gated-fusion RTL co-sim deferred，独立 PR 尚未创建
- disposition：进入 `in_review`；不得把 deferred co-sim 写成通过

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
