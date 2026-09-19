# T002：建立 FP32/INT8 软件 reference

- 状态：`planned`
- Sprint：Sprint 1
- 分支：`task/T002-software-reference`
- PR：待创建
- 依赖：T001
- 验收 skill：`thermo-nuclear-code-quality-review`

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
