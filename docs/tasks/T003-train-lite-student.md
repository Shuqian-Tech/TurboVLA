# T003：训练 TurboVLA-Lite student

- 状态：`planned`
- Sprint：Sprint 1
- 分支：`task/T003-train-lite-student`
- PR：待创建
- 依赖：T001、T002
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务要求

使用原始 TurboVLA 作为 teacher/reference，训练 tiny CNN + fusion + action MLP student。训练目标同时包含动作监督和 teacher action/feature 蒸馏，最终 checkpoint 必须符合固定 shape 和 INT8 校准约束。

## 交付物

- student checkpoint；
- 训练配置和数据版本；
- teacher/student action 对比报告；
- 目标 LIBERO 子集评测结果；
- 量化感知训练配置。

## 详细验收

- checkpoint 可由 T002 reference 加载；
- 没有动态长度或未定义算子；
- teacher/student action MAE 达到项目 owner 预先批准的阈值；
- 记录成功率、action MAE、参数量和推理 shape；
- thermo-nuclear review 确认模型配置没有堆积临时开关和特殊 case；
- PR 附带训练命令、checkpoint hash 和评测日志。
