# T012：最终 thermo-nuclear 审查与发布归档

- 状态：`in_progress`
- Sprint：Sprint 3
- 分支：`task/T012-final-acceptance`
- PR：[Shuqian-Tech/TurboVLA#1](https://github.com/Shuqian-Tech/TurboVLA/pull/1)（Draft）
- 依赖：T008、T009、T010、T011
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T012-final-acceptance`
- 发布 manifest：`docs/release/turbovla_lite_release_manifest.json`
- 审查报告：`docs/release/turbovla_lite_acceptance.md`
- 当前结果：`blocked_by_acceptance_gates`（T013 端到端 gate 已闭合；最终发布仍受独立任务 PR、正式 teacher/LIBERO 数据和 release timing closure 约束）
- 硬件 bring-up：T013 已提供 compatible `.bit.bin`/DTBO、Hardware Manager/JTAG、完整 PL inference 和 30 分钟稳定性证据；本任务保留独立发布 gate，不把 T013 证据扩写成正式机器人成功率或发布 timing closure。

## 验证记录

- 全仓 Python unit tests：此前带 PyTorch 环境通过，9 tests
- system Python 因缺少 `torch` 不能作为完整回归环境；使用仓库 `.venv` 执行 `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`，本次 9 tests 全部通过。
- T005 GEMM/Conv C simulation：通过
- T006 fusion/action C simulation：通过
- T009 runtime C simulation：通过
- T010 deterministic replay：通过
- T011 1000-cycle safety replay：通过
- `ruff`：新增 Python 文件通过
- KR260 device gate：使用 `/home/frank/WholeFile/FPGAs_AdaptiveSoCs_Unified_SDI_2025.1_0530_0145` 的离线 2025.1 installer 执行 `Add` 到 `/home/frank/AMD/vivado/2025.01`；Vivado Tcl `get_parts xck26-sfvc784-2LV-c` 返回 1 个精确匹配，`get_board_parts *kr260*` 返回 `xilinx.com:kr260_som:part0:1.0` 和 `1.1`；project smoke 创建成功并报告 `PROJECT_PART=xck26-sfvc784-2LV-c`。安装证据日志：`/tmp/turbovla-kria-add.log`、`/tmp/turbovla-vivado-device-check.log`、`/tmp/turbovla-device-smoke.K35df0/log`。
- Vitis HLS C simulation（T005/T006）：通过；GEMM/Conv/action RTL co-sim：通过。2026-09-20 原始双事务诊断运行在日志 `/tmp/turbovla-fusion-cosim-full.log` 完成第 1/2 事务后，`xsimk` 匿名 RSS 超过 96 GiB，按用户指定阈值终止；该日志不是通过证据。扩容及修复后的完整流程 `/tmp/turbovla-fusion-cosim-upgraded.log` 返回退出码 0，gated-fusion case 0、case 1 和 action MLP 均报告 `RTL Simulation : 1 / 1 [100.00%]` 并完成 C post-check；Hardware Manager/JTAG/hardware inference：`not_run`
- gated-fusion co-sim 修复：testbench 支持 `argv` case 0/1；Tcl 对两个 case 分别 setup/run，并将 XSIM launcher 注入 `-wdb /dev/null` 以避免 WDB 无界积累。修复后的完整 RTL co-sim 已在扩容主机完成，日志记录三个独立 XSIM 峰值约 `84057088 KB` 且进程均正常退出。
- 本机当前源码 Vivado 2025.1 全量重建返回 0；日志 `/tmp/turbovla-current-build.3zY7TN/vivado-current.log`；器件 `xck26-sfvc784-2LV-c`；post-route WNS `3.476 ns`、TNS `0`、WHS `0.010 ns` 是在实际 `96.974 MHz` 的 PL 时钟下测得，尚非文档目标 200 MHz；LUT `19.88%`、FF `13.25%`、DSP `2.00%`、BRAM `5.21%`、URAM `0%`，估算功耗 `2.741 W`；bitstream/XSA 和四份报告已在当前 checkout 的 `hardware/vivado_kr260/build/` 生成。
- 本机 HLS 日志 `/tmp/turbovla-current-build.3zY7TN/gemm-hls.log` 中 GEMM/Conv co-sim 均 `COSIM 212-1000 PASS`；`fusion-hls.log` 中 gated-fusion/action synthesis 和 IP export 通过，本机 31 GiB RAM 下跳过这两项 co-sim，保留扩容主机的历史通过记录，不混为本次通过。
- gated-fusion 跳过后的 action MLP 独立 synthesis、IP export 和 RTL co-sim：通过；历史日志 `/tmp/turbovla-fusion-skip-gated.log`，`RTL Simulation : 1 / 1`，`COSIM 212-1000 PASS`；完整流程中的 action MLP 结果见 `/tmp/turbovla-fusion-cosim-upgraded.log`
- 本机当前 FPGA artifact：`hardware/vivado_kr260/build/turbovla_kr260.bit`（SHA256 `c31f375d5f604d3fb57c890c986665e6a05f1f5d2c3749140f8f90dde9e2a2c6`）、`hardware/vivado_kr260/build/turbovla_kr260.xsa`（SHA256 `7566e039aa4776f43d41509c34def2129338026d93a9caf48b40aeae13282438`）；二者尚未转换为板端所需的 `.bit.bin/.dtbo`，且不能作为完整模型上板推理证据
- 板端只读探测记录：`hardware/vivado_kr260/reports/kr260_bringup_probe.md`；SSH 和 `/dev/fpga0` 可达，但活动 PL 是 `k26-starter-kits.bin`，未发现 TurboVLA device-tree 节点；本机 Hardware Manager 使用带 Vivado cable libraries 的 `hw_server` 仍返回 0 targets；bitstream download、PL DMA、hardware inference 和 30-minute stability 保持 `not_run`
- T013 merge update (2026-09-21)：PR #2 已通过 thermo-nuclear review 并合并到本分支（merge commit `2d69bc8`）；KR260 board evidence、30-minute parity stability 和 12-sample live power/temperature/rail capture 已归档于 `hardware/vivado_kr260/reports/t013_board_bringup.md`、`t013_board_live_sample.md` 和 `.csv`。上述旧 probe 行仅描述 T012 合并前的历史状态，不覆盖 T013 的新证据。

## 首次 FPGA 测试准备状态

- 已准备：KR260/K26 software-only bitstream、XSA、Vivado post-route 报告、寄存器表、runtime/replay model、参数包 checksum；Block Design 尚无 action MLP 实例或 DMA S2MM 返回通路。
- 首次加载前必须在 Hardware Manager 确认 active device 为 `xck26-sfvc784-2LV-c`，核对 bitstream/XSA SHA256，并保留下载日志。
- 当前状态：SSH/board probe 已完成；bitstream load、Hardware Manager/JTAG target、PL DMA、硬件 inference 和 30 分钟稳定性仍为 `not_run`；板上当前是 starter-kit overlay，不能把它写成 TurboVLA bring-up。
- 独立 PR：T012 Draft PR #1 已创建；T001-T011 的独立任务 PR 仍待创建

## Thermo-Nuclear Review

- review 时间：2026-09-20
- reviewer：Codex
- review 结果：`BLOCKED_BY_ACCEPTANCE_GATES`
- 结构/文件大小/抽象/分支/边界检查：无新增代码 blocking finding；GEMM、fusion/action、runtime、replay、safety 和 manifest 边界清晰
- code-judo 检查：T005 GEMM 被 T006 复用；contract/register map/manifest 避免重复 shape、offset 和 checksum 定义
- 本次增量检查（当前 `task/T012-final-acceptance` 分支与工作树 diff）：HLS launcher 61 行，两个 kernel Tcl 分别覆盖 GEMM/1x1 Conv 与 gated fusion/action MLP solution；无源码文件超过 1k 行，无新增 fallback 或散落的板卡分支
- 审查 finding：`tanh_q15` 的负小数区间最初受 C++ 向零整除影响；已改为显式 floor 区间并增加 `-1.5/+1.5` 回归用例，`python3 tools/run_fusion_action_csim.py` 通过
- blocking findings：独立任务 PR、正式 teacher/LIBERO 数据和 KR260 hardware inference bring-up 未完成；本机 Vivado 重建已补齐，但实际 PL 时钟未达到 200 MHz，仍缺板端 `.bit.bin/.dtbo`、action MLP/DMA 返回链、受控加载权限和实机推理证据
- disposition：保留 `in_progress`；gated-fusion 分阶段 co-sim 已通过并归档，本机 bitstream/XSA 已重建，但不可将该系统 bitstream 称为完整 TurboVLA-Lite PL 推理实现

### Follow-up review after board probe and software rerun

- review 时间：2026-09-20（本次工作树增量）
- reviewer：Codex
- review 结果：`PASS_WITH_ACCEPTANCE_GATES`
- structural checks：`git diff --check` 通过；当前增量只修改状态/发布记录、生成 manifest 和测试报告；新增或修改文件均低于 1k 行；Vivado 生成目录不作为源码审查对象
- abstraction/branching checks：manifest 仍由单一生成器负责 artifact/task 状态；没有新增 fallback、板卡分支、重复解析器或跨层状态机
- boundary checks：MVP 路径仍显式依赖 PL executor；board probe 只读且硬件状态保持 `not_run`；软件 replay latency 明确标为本机测量
- validation evidence：`.venv` unit tests 9/9、GEMM/Conv C simulation、fusion/action C simulation、runtime C simulation、replay、1000-cycle safety replay、contract、KR260 block manifest、Vivado baseline 和 ruff 全部通过
- blocking findings/disposition：独立任务 PR、正式 teacher/LIBERO 数据、200 MHz 时序验证、板端 `.bit.bin/.dtbo`、完整 PL action 输出链、受控加载权限和 hardware inference 仍缺失；当前源码 Vivado 构建已在本机复核，不以软件报告替代上板结果，继续保持 `in_progress`

### Local Vivado rebuild review

- review 时间：2026-09-20；reviewer：Codex；结果：`PASS_WITH_ACCEPTANCE_GATES`
- structural/code-judo：与 PR diff 共同复核，新增 HLS Tcl 跳过开关只影响本机测试编排；没有复制 kernel、添加 CPU fallback、扩大公共接口或引入额外硬件目标。当前增量源文件低于 1k 行，无新增跨层状态或一串特殊分支
- boundaries：bitstream/XSA 与板端 `.bit.bin/.dtbo`、software timing 与真实时钟、功耗估算与实测分开记录；旧本地产物已备份于 `/tmp/turbovla-current-build.3zY7TN/`
- disposition：代码层没有新增 blocking finding；200 MHz 目标未验证、action MLP/DMA 返回链缺失、受控加载与板端推理 `not_run`，不得标记 `accepted` 或 `done`

## 任务要求

对当前 MVP 分支和全部任务 PR 做最终结构、可维护性、边界、Vivado 工程和 runtime 归档审查。该任务是发布门，不是简单的文档整理。

## 交付物

- thermo-nuclear review report；
- 所有任务 PR/commit 清单；
- bitstream、XSA、参数包和 checksum；
- Vivado/HLS/功能/稳定性报告索引；
- 最终开发状态更新。

## 详细验收

- 完整执行 skill 中的 code-judo、文件大小、抽象、分支、边界和重复逻辑检查；
- 所有阻塞 findings 已解决或由项目 owner 书面豁免；
- 仅 KR260/K26 目标相关工程进入发布归档；
- 没有 DPU、Vitis AI 或 CPU inference fallback；
- 所有任务文件状态、Sprint 状态和 `docs/development_status.md` 一致；
- PR 合并前由 reviewer 明确写出 `accepted` 或 `blocked`，不得只写“looks good”。
