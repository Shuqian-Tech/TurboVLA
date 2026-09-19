# T010：实现数据回放与数值对齐测试

- 状态：`planned`
- Sprint：Sprint 3
- 分支：`task/T010-replay-validation`
- PR：待创建
- 依赖：T009
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务要求

建立从 Python golden tensors 到 KR260 实机的 deterministic replay，比较每层或每个 kernel 的输出、最终 action、延迟和 DDR 带宽。

## 交付物

- replay input bundle；
- host/reference comparator；
- FPGA output capture；
- 数值和性能报告。

## 详细验收

- 同一个输入 bundle 在软件和 FPGA 上可重复运行；
- 每个 kernel 的误差定位到 tensor/layer；
- action MAE、最大误差和 latency p50/p99 自动生成；
- 不允许手工修改输出或跳过失败样本；
- thermo-nuclear review 确认测试编排没有重复解析器和隐式状态；
- PR 附带失败样本处理规则和报告。
