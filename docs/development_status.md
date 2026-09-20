# TurboVLA KR260 开发状态

## 当前状态

- 更新时间：2026-09-19
- 项目状态：`in_progress`
- 当前目标：在 KR260 上完成不使用 DPU、神经推理全部在 PL 的 TurboVLA-Lite MVP
- 当前 Sprint：[Sprint 3：Runtime、闭环与发布验收](sprint/sprint-3-runtime-acceptance.md)
- 当前任务：[T012：最终 thermo-nuclear 审查与发布归档](tasks/T012-final-acceptance.md)（`in_progress`）
- 唯一编译平台：AMD Kria KR260/K26
- Vivado 直接调用：使用仓库内 Tcl/HLS flow
- KR260 SSH：`ubuntu@192.168.68.123`（不在仓库保存凭据）
- 开发板状态：当前不稳定/不可作为验证前置条件
- 当前验证模式：纯软件 Vivado，目标器件仍固定为 KR260/K26
- Vivado Hardware Manager：暂不作为 T001-T008 验证门；实机 bring-up 阶段再验证 active target/device
- `fpl26` MCP：当前环境未发现资源或模板，后续可用时接入

## 已完成

- [x] 记录 KR260 纯 FPGA 总体架构
- [x] 确认不使用 DPU，PL 承担神经网络推理
- [x] 建立 Vivado/HLS 编译与优化流程
- [x] 收敛 TurboVLA-Lite MVP 边界
- [x] 建立 Sprint 1/2/3 和逐任务文档结构

## 进行中

- [ ] T001：冻结 MVP 模型与接口契约（`in_review`）
- [ ] T002：建立 FP32/INT8 软件 reference（`in_review`）
- [ ] T003：训练 TurboVLA-Lite student（`in_progress`）
- [ ] T004：生成 FPGA 参数包（`in_progress`）
- [ ] T005：实现 INT8 GEMM/Conv IP（`in_progress`）
- [ ] T006：实现 Fusion 与 Action MLP IP（`in_progress`）
- [ ] T007：搭建 KR260 Vivado Block Design（`in_progress`）
- [ ] T008：完成综合、布局布线和报告基线（`in_progress`）
- [ ] T009：实现 PS DMA/AXI-Lite Runtime（`in_progress`）
- [ ] T010：实现数据回放与数值对齐测试（`in_progress`）
- [ ] T011：完成机器人闭环与稳定性测试（`in_progress`）
- [ ] T012：最终 thermo-nuclear 审查与发布归档（`in_progress`）

## 未开始

- [ ] T006-T008：Fusion/Action kernel 和 Vivado block design
- [ ] T009-T012：runtime、回放、闭环和发布验收

## 当前阻塞

- Vivado 本地安装路径无效；需要修复软件 Vivado 环境后才能运行 synthesis/implementation/post-route 验证。
- KR260 开发板当前不可作为验证前置条件；SSH/JTAG 实机状态记为 `not_run`，不阻塞软件阶段。
- 尚未拥有训练 checkpoint；T002 当前使用确定性占位 instruction table，正式表待 T003/T004 生成。
- T003 当前只有确定性 smoke checkpoint；真实 teacher checkpoint、LIBERO 蒸馏数据和正式成功率尚未生成。
- T004 当前参数包来自 smoke checkpoint；正式 student checkpoint 替换前不宣称发布参数包。
- Vivado wrapper 可执行文件存在但目标路径无效；T005 当前仅有 portable C simulation，未宣称 HLS/Vivado 结果。
- 尚未建立第一个 Vivado KR260 工程和 post-route baseline。
- T001 独立 PR 被 GitHub 权限阻塞：当前身份 `frankdede` 无法 push 到 `H-EmbodVis/TurboVLA`。
- 本地环境未安装 `ruff`，T002 lint 证据暂缺；当前 Vivado wrapper 仍指向不存在的 `/home/frank/AMDDesignTools/2026.1/Vivado/bin/vivado`。

## T002 软件 reference 证据

- 固定 shape NumPy FP32/INT8 reference 已实现于 `turbovla/lite_reference.py`，包含 tiny CNN、instruction embedding lookup、两层 gated fusion、state projection 和 12x7 action MLP。
- `python3 -m unittest discover -s tests -v`：4 tests 通过；契约校验、calibration、golden 生成和逐层自比较通过。
- INT8 action 相对 FP32：`max_abs_error=0.0007072217`，`mean_abs_error=0.0001537027`；golden SHA256 为 `307600ad7f29001fee8335921e9d3eaa3bceca8e6383c65252688f2f58390f28`。
- thermo-nuclear review：`PASS_WITH_ENVIRONMENT_BLOCKER`，无代码 blocking finding；ruff/Vivado/PR 权限阻塞已记录。

## T003 student 训练证据

- `.venv` 已安装 PyTorch 2.14.0 和 NumPy 1.26.4；固定模型实现于 `turbovla/lite_student.py`。
- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：6 tests 通过。
- 3-step smoke training 参数量 `148948`，action L1 从 `0.0628083` 降至 `0.0491720`；teacher-action L1 从 `0.0631098` 降至 `0.0490225`。
- smoke 报告：`tests/data/lite_student_smoke_report.json`；正式 LIBERO 成功率尚未宣称。

## T004 参数包证据

- `turbovla/lite_parameter_pack.py` 实现 little-endian、64-byte alignment、INT8 weight/FP32 bias、scale 和 checksum manifest。
- smoke 导出 19 个 tensor、150528 bytes；loader checksum、reference reconstruction 和 round-trip 单测通过。
- weights SHA256：`2c6f6081e92ddcf5ffcc22b706f8c0eb7b5c293eae357d5c78afd9d6acb3242`；manifest SHA256：`67c1ce537ed6cad7427e8ebdac55d72da27bacb7db66d1776a53df92504d99993`。

## 状态规则

任何任务完成后必须同步更新任务文件、所属 Sprint 文件和本文件。任务只有在独立 PR 合并、Vivado/功能证据齐全、并通过 `thermo-nuclear-code-quality-review` 后才能进入 `done`。

## T005 kernel 证据

- `hardware/hls/gemm/gemm.cpp` 提供固定上界 INT8 GEMM 和 1x1 Conv，累加器为 INT32，支持 HLS AXI interface directives。
- `python3 tools/run_gemm_csim.py`：通过；`g++ -std=c++17 -O2 -Wall -Wextra -Werror`。
- Vivado/HLS co-simulation、synthesis、post-route：`not_run`，工具路径无效；硬件 bring-up：`not_run`。

## T008 baseline 证据

- `hardware/vivado_kr260/report_manifest.template.json` 固定 KR260/K26、software-only 和 hardware `not_run` 语义。
- `python3 tools/validate_vivado_baseline.py ... --allow-not-run`：通过；默认模式拒绝未完成的报告状态。
- 真实 bitstream/XSA、post-route timing、utilization、power、CDC：`not_run`，不使用模板冒充结果。

## T009 runtime 证据

- `runtime/` 提供 host/replay C++ register/DMA model；runtime 通过显式 PL executor 接口运行，不包含 CPU inference fallback。
- `python3 tools/run_runtime_csim.py`：通过；正常提交、版本拒绝、instruction 越界和 DMA timeout 均验证。
- 实机 DMA/cache/interrupt 和 Hardware Manager：`not_run`。

## T010 replay 证据

- `tools/run_lite_replay.py` 从 T002 golden bundle 重放 FP32/INT8 reference，自动比较每层和 action，不允许手工跳过样本。
- `tests/data/lite_replay_report.json`：INT8 action replay `max_abs_error=0.0`、`mean_abs_error=0.0`；本次 software-only INT8 p50/p99 `5.3749/7.9713 ms`。
- HLS/RTL/Vivado target replay、DDR 带宽和实机回放：`not_run`。

## T011 stability 证据

- `turbovla/safety.py` 集中实现 action limit、NaN 拒绝、timeout、emergency stop 和通信断开策略。
- `tests/data/lite_stability_report.json`：1000/1000 software-only cycles accepted，max drift `0.0`，四类故障注入全部命中。
- 真实机器人/开发板 30 分钟稳定性、温度、功耗和成功率：`not_run`。

## T012 final acceptance 证据

- `tools/generate_release_manifest.py` 生成 `docs/release/turbovla_lite_release_manifest.json`，收集 T001-T012 状态、当前 commit、artifact checksum 和阻塞 gate。
- `docs/release/turbovla_lite_acceptance.md` 完成 thermo-nuclear 汇总，结果为 `BLOCKED_BY_ACCEPTANCE_GATES`。
- 所有软件-only C/Python replay/safety 检查通过；独立 PR、Vivado/HLS、bitstream/XSA、KR260 bring-up 仍未通过。

## T007 block design 证据

- `hardware/vivado_kr260/` 已建立 KR260-only project/build Tcl、block design Tcl、200 MHz XDC 和 register map。
- `python3 tools/validate_kr260_block_manifest.py`：通过，15 registers 与 T001 contract 一致。
- Tcl 对缺少 T005/T006 packaged IP 直接 fail-fast；Vivado validation、bitstream/XSA 和 Hardware Manager：`not_run`。

## T006 fusion/action 证据

- `hardware/hls/fusion_action/fusion_action.cpp` 复用 T005 GEMM，实现固定 shape gated fusion、state projection 和 12x7 action MLP。
- `python3 tools/run_fusion_action_csim.py`：通过；hard-sigmoid/tanh 路径和零权重 action 输出均验证。
- HLS/Vivado 报告和硬件 bring-up：`not_run`，不冒充软件 C simulation 结果。
