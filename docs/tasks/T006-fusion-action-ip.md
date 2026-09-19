# T006：实现 Fusion 与 Action MLP IP

- 状态：`planned`
- Sprint：Sprint 2
- 分支：`task/T006-fusion-action-ip`
- PR：待创建
- 依赖：T005
- 验收 skill：`thermo-nuclear-code-quality-review`

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
