# Distilled TurboVLA on FPGA

该文档域描述 TurboVLA-Lite 从 teacher/student、蒸馏和 QAT 到 KR260 PL 推理、
PS runtime 与闭环验证的完整路径。

## 导航

- [Latest status](latest-status.md)
- [Sprint 索引](sprints/README.md)
- [Task 索引](tasks/README.md)
- [MVP 边界](../mvp.md)
- [模型与接口合同](../contracts/turbovla_lite_contract.md)
- [KR260 FPGA 设计](../turbovla_kr260_fpga_design.md)
- [Vivado 流程](../vivado_flow.md)
- [发布验收](../release/turbovla_lite_acceptance.md)

## 固定边界

- 唯一部署目标是 AMD Kria KR260/K26；
- 神经推理全部在 FPGA PL；
- PS 只负责 I/O、buffer、cache、AXI-Lite、调度、安全和机器人通信；
- 不使用 DPU、Vitis AI 或 CPU inference fallback；
- GPU 只用于离线训练和评估，不是部署目标。
