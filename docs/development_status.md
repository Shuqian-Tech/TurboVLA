# TurboVLA KR260 开发状态

## 当前状态

- 更新时间：2026-09-19
- 项目状态：`in_progress`
- 当前目标：在 KR260 上完成不使用 DPU、神经推理全部在 PL 的 TurboVLA-Lite MVP
- 当前 Sprint：[Sprint 1：模型与硬件契约](sprint/sprint-1-model-contract.md)
- 当前任务：[T001：冻结 MVP 模型与接口契约](tasks/T001-freeze-mvp-contract.md)（`in_review`）
- 唯一编译平台：AMD Kria KR260/K26
- Vivado 直接调用：使用仓库内 Tcl/HLS flow
- KR260 SSH：`ubuntu@192.168.68.123`（不在仓库保存凭据）
- Vivado Hardware Manager：用户已确认已连接 KR260；硬件任务开始前仍需验证 active target/device
- `fpl26` MCP：当前环境未发现资源或模板，后续可用时接入

## 已完成

- [x] 记录 KR260 纯 FPGA 总体架构
- [x] 确认不使用 DPU，PL 承担神经网络推理
- [x] 建立 Vivado/HLS 编译与优化流程
- [x] 收敛 TurboVLA-Lite MVP 边界
- [x] 建立 Sprint 1/2/3 和逐任务文档结构

## 进行中

- [ ] T001：冻结 MVP 模型与接口契约（`in_review`）

## 未开始

- [ ] T002-T004：软件 reference、蒸馏和 FPGA 参数包
- [ ] T005-T008：HLS/RTL kernel 和 Vivado block design
- [ ] T009-T012：runtime、回放、闭环和发布验收

## 当前阻塞

- 尚未确认 Vivado 版本和可用的 PetaLinux/Ubuntu runtime；KR260 SSH 地址已记录，Hardware Manager 连接由用户确认但尚未本地验证。
- 尚未拥有 TurboVLA-Lite 的训练 checkpoint 和 instruction embedding table。
- 尚未建立第一个 Vivado KR260 工程和 post-route baseline。

## 状态规则

任何任务完成后必须同步更新任务文件、所属 Sprint 文件和本文件。任务只有在独立 PR 合并、Vivado/功能证据齐全、并通过 `thermo-nuclear-code-quality-review` 后才能进入 `done`。
