# T016：重写 README 实验结果首页

- 状态：`in_review`
- Sprint：Sprint 3
- 分支：`task/T016-readme-experiment-results`
- PR：待创建
- 依赖：T009、T013、T014、T015
- Hardware bring-up：复用既有 T013/T015 证据，本任务不重新配置开发板
- 验收 skill：`thermo-nuclear-code-quality-review`

## 目标

将根 `README.md` 从上游 RTX 4090 论文说明重构为 TurboVLA-Lite KR260
实验报告，按真实实现顺序展示模型、HLS/RTL、Vivado 和板端结果，并记录每个
有日志证据的 simulation/build/runtime 阶段耗时。

## 验收标准

- README 明确 KR260/K26 唯一部署目标、纯 PL 神经推理和 PS/PL 边界；
- 实现流程按模型导出、C simulation、HLS、RTL co-simulation、Vivado、板端顺序排列；
- simulation 和 build 时间只使用原始日志中的显式 elapsed 或起止时间；
- 区分 RTL 墙钟时间、HLS 理想 kernel latency 和板端端到端 latency；
- 区分 LIBERO 成功率、FPGA 调用/parity 通过率和真实机器人结果；
- 所有本地证据链接存在，`git diff --check` 通过；
- thermo-nuclear review 无未处置 blocking finding。

## 变更与验证

- 变更文件：`README.md` 及 T016 状态记录；无实现代码或硬件产物变更。
- 时间来源：T015 case 0/cases 1-5 HLS 日志和 Vivado batch 日志。
- 结果来源：T013/T015 报告、T015 100-sample JSON、T014 evaluation。
- 验证：`git diff --check -- README.md` 通过；README 本地链接检查通过；
  csynth latency 和 validation sweep JSON 关键数值已逐项复核。

## Thermo-nuclear review

- 日期：2026-09-22；reviewer：Codex
- 范围：`origin/main...task/T016-readme-experiment-results` 的文档 diff
- 结果：`PASS`，无 blocking finding
- 结构简化：根 README 从 272 行缩短为 237 行，围绕单一实验流程组织；没有新增
  wrapper、模式、条件分支或重复实现
- 文件规模：没有文件跨越 1,000 行门槛；README 保持分节和证据索引
- 抽象/分支/边界：无源码抽象或 branching 变化；FPGA/PS、simulation/board、
  parity/success-rate 边界均显式说明
- 发现处置：无 finding；未记录的训练总耗时明确标为“未单独记录”，没有估算
- 证据：`hardware/vivado_kr260/reports/t015/`、
  `hardware/vivado_kr260/reports/t013/`、
  `docs/evaluation/t014_gpu_tinycnn_pilot.md`
