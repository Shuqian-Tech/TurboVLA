# TurboVLA KR260 开发状态

## 当前状态

- 更新时间：2026-09-24
- 项目状态：`in_progress`
- 当前目标：在 KR260 上完成不使用 DPU、神经推理全部在 PL 的 TurboVLA-Lite MVP
- 当前 Sprint：[Sprint 3：Runtime、闭环与发布验收](sprint/sprint-3-runtime-acceptance.md)（已进入）
- 当前任务：[T010：实现数据回放与数值对齐测试](tasks/T010-replay-validation.md)
  与 [T017：最小模块化 ALP 探索、开发与验证框架](tasks/T017-minimal-alp-explorer.md)
  （T010 `in_progress`，T017 `in_review`）；T009 已完成并合并 PR #9
- 唯一编译平台：AMD Kria KR260/K26
- Vivado 直接调用：使用仓库内 Tcl/HLS flow
- KR260 SSH：`amd-edf@192.168.68.120`（passwordless key；不在仓库保存凭据）
- 开发板状态：T013 既有 bitstream/DTBO 证据仍有效；T015 正确板端 `amd-edf@192.168.68.120` 已加载 package，probe、action parity 和 12 次 live invocation 通过；其他地址不作为证据
- 当前验证模式：KR260/K26 软件 Vivado + 独立实机 bring-up 证据
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
- [x] T004：生成 FPGA 参数包（`done`；正式 QAT/v0.3 参数包、PL parity、Vivado 和 KR260 bring-up 已通过）
- [ ] T005：实现 INT8 GEMM/Conv IP（`in_review`）
- [ ] T006：实现 Fusion 与 Action MLP IP（`in_review`）
- [ ] T007：搭建 KR260 Vivado Block Design（`in_progress`）
- [ ] T008：完成综合、布局布线和报告基线（`in_progress`）
- [x] T009：实现 PS DMA/AXI-Lite Runtime（`done`；PR #9 merged，commit `737e964`）
- [ ] T010：实现数据回放与数值对齐测试（`in_progress`）
- [ ] T011：完成机器人闭环与稳定性测试（`in_progress`）
- [ ] T012：最终 thermo-nuclear 审查与发布归档（`in_progress`）
- [x] T013：补齐 PL 推理链、PS Runtime 与端到端 action 数值对齐（`accepted`；PR #2 已合并到 PR #1，merge commit `2d69bc8`）
- [x] T014：GPU TinyCNN 学习能力评估（`done`；100-episode 蒸馏 FP32/PTQ/QAT 为 `75/100`、`77/100`、`78/100`，teacher `95/100`；depthwise 消融无闭环收益，决策 `keep_pointwise`；PR #3 已合并）
- [x] T015：升级 state INT8 scale 合同（`done`；模型不变，v0.3 model header 增加 checkpoint-calibrated state scale；100-sample KR260 validation sweep 已通过；PR #4 已合并，merge commit `ff97126dd4a495ca36116cb75b65f9952c556a0c`）
- [x] T016：重写 README 实验结果首页（`done`；流程顺序、simulation/build/runtime 耗时、实验结果和证据链接已核验；PR #11）
- [ ] T017：最小模块化 ALP 探索、开发与验证框架（`in_review`；V0、45 tests、8/8 software profile 和 thermo-nuclear review 已通过；替代 PR 待创建）

## 未开始

- [x] T007-T008：当前 HLS 源码对应的 Vivado 全量重建、post-route 报告、bitstream 和 XSA 已完成
- [ ] T010-T012：回放、闭环和发布验收

## 当前阻塞

- Vivado v2025.1 已识别 `xck26-sfvc784-2LV-c`；当前机器已从本地 HLS IP 完成 block design validation、synthesis、implementation、post-route timing、bitstream 和 XSA，日志 `/tmp/turbovla-current-build.3zY7TN/vivado-current.log`，本地 `build/` 产物可复核。
- 初始只读 probe 的 starter-kit 状态已被 T013 实机结果取代：TurboVLA overlay 已加载，PL0 clock 自动启用，完整 PL inference 和 30 分钟稳定性通过。旧 probe 仍保留为加载前历史记录。
- T002 的历史 golden 仍使用确定性参数；正式 teacher cache、student checkpoint 和闭环成绩已由 T014 生成，但 T003/T004 自身的独立 PR/验收记录仍需补齐。
- T004 已从选定 QAT checkpoint 生成 v0.3 正式参数包，并在精确 commit `2b88e7f` 通过软件 exact INT8、HLS/RTL、Vivado、KR260 package 和 `.120` 板端 action parity gate；T004 PR #6 已合并，merge commit `2c7f597057bb85ff2c9bf826505b3ba30ed79bf1`。
- T014 baseline、蒸馏、扩大评测和 depthwise 容量消融已完成：固定 split 的 3-seed FP32 validation MAE 为 `0.127903 +/- 0.000432`；同一批 100 episodes 的蒸馏 FP32/PTQ/QAT 为 `75/100`、`77/100`、`78/100`，teacher 为 `95/100`。新增两个 `3x3 depthwise + 1x1 pointwise` block 后，匹配续训 action MAE 为 `0.12505184`，对照为 `0.12505893`；task 8/9 闭环两者均为 `9/20`，没有结构收益。决策为 `keep_pointwise`，不更新 FPGA 合同；T014 PR #3 已合并，正式 QAT 参数包和 PL parity 已由 T004/T015 关闭。
- T015 state-scale audit 发现正式 QAT 的 `state_input_scale=0.0254367618`，而 v0.2 PL 硬编码 `1/127`；验证 state 最大绝对值 `3.23046875`。保持旧 ABI 重做 QAT 仅 `20/30`，因此 owner 决定升级合同而不修改模型。v0.3 使用现有 model header 保留区传递 scale。
- T015 精确 commit `2b88e7f` 已通过 35 tests、runtime C-sim、正式 QAT pack 的 HLS C-sim、6 个独立 RTL co-sim case、Vivado 全量重建、package 和 `.120` 板端 parity；`model.bin` SHA256 为 `6df32b27eb8a730027c6f37af8c8bd33058700293941a44eae6ade0697fa3886`，正式 replay action max error 为 `5.96046e-08`。case 0 XSIM peak `111802256 KB`，不宣称低于 96 GiB；板端 action parity `max_abs_error=1.19209e-07`，12/12 live invocations 和追加 10 个 validation 样本均通过。追加样本中 QAT 到 exact INT8 action MAE 增加 `0.0003444`，gripper sign accuracy 下降 `0.917 pp`；FPGA 到 exact INT8 的误差仍低于 `1.8e-07`。
- T015 `.120` 实机性能：PL0 实际 `199.998 MHz`；20 次正式 replay `executor.run()` 平均 `77.162 ms`，整体推理频率 `12.960 Hz`，端到端时间包含 cache/MMIO/polling 开销。HLS 最大 `3,817,800 cycles` 在该频率下为 `19.089 ms`（理想 kernel 上限 `52.386 Hz`），不把它冒充实测端到端 latency。随后对固定 validation split 的 100 个不同样本完成全程监控的真实 sweep：`100/100` 成功，mean/p95 latency `77.449/78.440 ms`，整体 `12.9118 Hz`，FPGA 对 exported exact INT8 worst max/mean error `1.78814e-07/2.39594e-08`；整板功耗 `3.64..4.09 W`（均值 `3.731 W`）、PL 温度 `25.024..28.490 C`（均值 `26.878 C`）、Linux load1 `1.02..2.06`、可用 RAM `3481.7..3497.9 MiB`。原始证据在 `hardware/vivado_kr260/reports/t015/validation100_board_sweep.json`、`validation100_board_run_summary.csv` 和 `validation100_board_sensors.csv`。旧的同一 fixture 100 次仅保留为先前 sanity check，不再作为 validation 负载结论。
- T015 软件与板端证据、thermo-nuclear review 已归档于 `hardware/vivado_kr260/reports/t015/`；review 结果 `PASS_WITH_DEVICE_AND_PR_GATES`，`.119` XRT headers 和 Draft PR 仍是外部 gate。
- Vivado v2025.1 当前 wrapper 指向 `/home/frank/AMDDesignTools/2025.1/2025.1/Vivado`；本机 GEMM/Conv RTL co-sim 通过。2026-09-20 原始双事务诊断运行完成第 1/2 事务后，XSIM 匿名 RSS 超过用户指定的 96 GiB 阈值并终止；随后加入 case 0/1 事务拆分和 `-wdb /dev/null` footprint 修复，并在扩容主机上完成完整流程：日志 `/tmp/turbovla-fusion-cosim-upgraded.log` 返回退出码 0，gated-fusion case 0/1 和 action MLP 均 `RTL Simulation : 1 / 1` 且 C post-check 通过。本机 31 GiB RAM 的这次构建只重复这两个 kernel 的 synthesis/IP export，不重跑其高内存 co-sim。
- 已建立当前源码对应的 KR260 Vivado post-route baseline；软件报告 manifest 在 `hardware/vivado_kr260/report_manifest.json`，状态为 `current_source_verified`。
- upstream 已切换到 `git@github.com:Shuqian-Tech/TurboVLA.git`；T012 PR [#1](https://github.com/Shuqian-Tech/TurboVLA/pull/1) 已合并到 `main`（merge commit `000f03d`），T009 PR #9 已合并（merge commit `737e964`）；T001-T008/T010-T011 的独立任务 PR 仍缺失，发布流程 gate 尚未关闭。
- Kria device package 已由 `/home/frank/WholeFile/FPGAs_AdaptiveSoCs_Unified_SDI_2025.1_0530_0145` 的离线 2025.1 installer 非交互 Add 到现有 Vivado；Tcl 验证 `xck26-sfvc784-2LV-c` 与 `xilinx.com:kr260_som:part0:1.0/1.1` 可见。完整源码 Vivado 重建已完成；认证信息不写入仓库。

## T002 软件 reference 证据

- 固定 shape NumPy FP32/INT8 reference 已实现于 `turbovla/lite_reference.py`，包含 tiny CNN、instruction embedding lookup、两层 gated fusion、state projection 和 12x7 action MLP。
- `python3 -m unittest discover -s tests -v`：4 tests 通过；契约校验、calibration、golden 生成和逐层自比较通过。
- INT8 action 相对 FP32：`max_abs_error=0.0007072217`，`mean_abs_error=0.0001537027`；golden SHA256 为 `307600ad7f29001fee8335921e9d3eaa3bceca8e6383c65252688f2f58390f28`。
- thermo-nuclear review：`PASS_WITH_KR260_DEVICE_GATE`，无代码 blocking finding；KR260 device package、正式训练数据和 PR 权限阻塞已记录。

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
- Vitis HLS C simulation：T005 `gemm/conv C simulation passed`、T006 `fusion/action C simulation passed`；GEMM/Conv/action `COSIM 212-1000 PASS`。gated-fusion testbench 支持 `argv=0/1` 分事务运行，Tcl 自动关闭 WDB；完整 case 0/1 RTL co-sim 已通过并记录于 `/tmp/turbovla-fusion-cosim-upgraded.log`，硬件 bring-up：`not_run`。

## T008 baseline 证据

- `hardware/vivado_kr260/report_manifest.template.json` 固定 KR260/K26、software-only 和 hardware `not_run` 语义；真实结果记录于 `hardware/vivado_kr260/report_manifest.json`。
- `python3 tools/validate_vivado_baseline.py hardware/vivado_kr260/report_manifest.json`：通过；当前源码 timing/utilization/power/CDC 均为 `passed`，hardware bring-up 仍单独保持 `not_run`。
- 本机当前源码 bitstream/XSA、post-route timing、utilization、power、CDC 报告通过 software-only 构建；WNS `3.476 ns`、TNS `0`、WHS `0.010 ns`、功耗估算 `2.741 W`、LUT `19.88%`、FF `13.25%`、DSP `2.00%`、BRAM `5.21%`、URAM `0%`。`clk_pl_0` 实际约 `96.974 MHz`，不是 200 MHz 验收；功耗受 reset 活动告警影响，CDC 不覆盖未约束输入端口。

## T009 runtime 证据

- `runtime/` 提供 XRT arena、cache maintenance、UIO AXI-Lite 和 host fake-MMIO；runtime 只调用显式 PL executor，不包含 CPU inference fallback。
- `python3 tools/run_runtime_csim.py` 和 ASan/UBSan：通过；normal submit、TOW interrupt acknowledge、timeout recovery、invalid model replacement、instruction bounds、unknown error 和 non-finite action 均验证。
- 完整 Python 回归 35 tests、contract/register validators 和 scoped ruff 通过。
- 精确 source commit `281d7d4` 在 `.120` KR260 独立 worktree 构建；5/5 validation fixtures action parity 通过，worst max error `8.94070e-08`，mean runtime call latency `76.087 ms`，每次捕获 completion ISR `0x1` 并在返回前清为 `GIE/IER/ISR=0/0/0`；FPGA manager 最终 `operating`。
- thermo-nuclear review：`PASS`，ISR TOW、pending interrupt 和 invalid-model stale-state findings 均已解决；真实 destructive timeout/reset fault injection 未运行，平台级 PL reset 不作宣称。

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
- 所有已运行的 software-only C/replay/safety/HLS 检查通过；独立 PR、正式 teacher/LIBERO 数据和 KR260 hardware inference bring-up 仍未闭合。T012 的历史记录早于当前 T015 package；T015 已生成 `.bit.bin/.dtbo`，但因板端网络不可达仍不能宣称 T015 完整 PL 推理已上板。
- system Python 因缺少 `torch` 不能作为完整回归环境；仓库 `.venv` 已存在并提供 PyTorch/NumPy，使用 `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v` 的本次回归为 9 tests 通过。

## T013 end-to-end integration

- 独立分支 `task/T013-pl-runtime-e2e` 已开始；任务合同见 `docs/tasks/T013-pl-runtime-e2e.md`。
- 高内存 HLS/Vivado 作业固定在 `frank@192.168.68.119` 的隔离 worktree 运行，源代码只通过 GitHub branch/PR 交接；不会覆盖该机器现有 `/home/frank/TurboVLA` 脏工作区。
- 单一 HLS AXI4-MM/AXI-Lite top 已替换未连接的 AXI DMA 与不完整 kernel 组合，真实 PS buffer/MMIO/cache runtime 边界和 84-value action parity 已闭合。
- 2026-09-21 项目 owner 将 T013 首版上板的 WNS/TNS 改为 reporting-only；任何负 slack 只允许以 `bringup_owner_waived` 进入 bring-up，报告不得写成 timing clean，发布验收前仍必须完成时序收敛。
- T013 200 MHz Vivado backend 已完成：post-route WNS `+0.002 ns`、TNS `0`、WHS `+0.010 ns`、THS `0`，LUT `29.29%`、FF `16.46%`、DSP `13.46%`、BRAM `5.21%`、估算功耗 `3.185 W`；bitstream/XSA 已生成。
- KR260 首次完整 PL inference 已通过，84 个 action 与 golden 对齐（max absolute error `1.86265e-09`、mean absolute error `4.14556e-10`）。首次锁机根因是旧 DTBO 的 `generic-uio` 不会启用 PL0 clock；commit `ee22fc1` 增加 `xlnx,fclk` consumer，overlay 从 `CLKACT=0` 加载后自动得到 `pl0_ref enable_count=1`，probe/full inference 均无需手写寄存器。证据见 `hardware/vivado_kr260/reports/t013_board_bringup.md`。
- 2026-09-21 追加 12-sample live load capture：12/12 次 PL inference 成功；`Temp_PL` 29.003-31.396 C，INA260 board power 3.350-3.440 W，VCCINT 719-721 mV，VCCBRAM 841-846 mV；overlay、FPGA manager 和 PL0 clock 全程稳定。原始数据见 `hardware/vivado_kr260/reports/t013_board_live_sample.csv`，统计与边界说明见同目录 Markdown。
- T013 exact-vector RTL co-sim 在 exact commit `dc31221` 完成 `2/2`，C post-check parity 与 invalid-instruction gate 通过，runner exit 0；30 分钟板端运行完成 17,019 次完整 parity 检查，温度/功耗稳定。最终 thermo-nuclear review 为 `PASS`，无剩余 blocking finding；PR #2 已于 2026-09-21 合并到 PR #1（merge commit `2d69bc8`），T013 状态为 `accepted`。

## T007 block design 证据

- `hardware/vivado_kr260/` 已建立 KR260-only project/build Tcl、block design Tcl、200 MHz XDC 和 register map。
- `python3 tools/validate_kr260_block_manifest.py`：通过，15 registers 与 T001 contract 一致。
- Tcl 对缺少 T005/T006 packaged IP 直接 fail-fast；KR260 block design/bitstream/XSA 的本地归档可通过 manifest 校验，Hardware Manager/JTAG 和板端推理仍 `not_run`。

## T006 fusion/action 证据

- `hardware/hls/fusion_action/fusion_action.cpp` 复用 T005 GEMM，实现固定 shape gated fusion、state projection 和 12x7 action MLP。
- `python3 tools/run_fusion_action_csim.py`：通过；hard-sigmoid/tanh 路径和零权重 action 输出均验证。
- HLS C simulation、synthesis、IP export 已通过；action MLP RTL co-sim 通过（`/tmp/turbovla-fusion-skip-gated.log`，并在完整流程中复核）。gated-fusion case 0/1 已完成事务拆分和无 WDB launcher 修复后的 RTL co-sim；当前 HLS IP 的 Vivado 全量重建已通过，硬件 bring-up 仍 `not_run`。
