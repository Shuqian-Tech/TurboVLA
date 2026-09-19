# T004：生成 FPGA 参数包

- 状态：`planned`
- Sprint：Sprint 1
- 分支：`task/T004-export-fpga-parameters`
- PR：待创建
- 依赖：T002、T003
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务要求

将 student checkpoint 转换为 FPGA 可加载的 INT8/INT32 参数包，生成 instruction embedding table、scale、bias、metadata 和版本 manifest。参数布局必须与 kernel 读取顺序一致。

## 交付物

- 权重二进制文件；
- instruction embedding table；
- scale/bias/zero-point 文件；
- 参数 manifest 和 checksum；
- Python loader 与 reference replay。

## 详细验收

- 每个参数有 dtype、shape、offset 和 checksum；
- loader 能完整重建 T002 reference 所需参数；
- endian、对齐、stride 和 padding 有测试；
- 参数包不依赖运行时 Python；
- thermo-nuclear review 确认参数转换没有散落的格式特判；
- PR 附带 manifest、大小统计和 replay 结果。
