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
- 当前结果：`blocked_by_acceptance_gates`
- 硬件 bring-up：SSH reachability check passed；bitstream load、Hardware Manager/JTAG、hardware inference：`not_run`

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
- 另一台机器声明完成当前源码的 Vivado 2025.1 全量重建；日志 `/tmp/turbovla-vivado-current.log` 和非忽略 bitstream/XSA 未随 checkout 提供，当前机器不能独立复核该声明。当前 checkout 的本地归档 manifest 校验通过，但仍按 software-only 证据处理。
- gated-fusion 跳过后的 action MLP 独立 synthesis、IP export 和 RTL co-sim：通过；历史日志 `/tmp/turbovla-fusion-skip-gated.log`，`RTL Simulation : 1 / 1`，`COSIM 212-1000 PASS`；完整流程中的 action MLP 结果见 `/tmp/turbovla-fusion-cosim-upgraded.log`
- 首次 FPGA 测试准备 artifact：`hardware/vivado_kr260/build/turbovla_kr260.bit`（SHA256 `c61ce3c97acaeabe2d57d1c50a657d64181807efc4a24fd81541245a6c049c79`）、`hardware/vivado_kr260/build/turbovla_kr260.xsa`（SHA256 `0cea12b20853ab22f9b532347678f25054aa5b8f9fcc44505fea6b0ab02fe83a`）、当前参数包和 `docs/release/turbovla_lite_release_manifest.json`
- 板端只读探测记录：`hardware/vivado_kr260/reports/kr260_bringup_probe.md`；SSH 和 `/dev/fpga0` 可达，但活动 PL 是 `k26-starter-kits.bin`，未发现 TurboVLA device-tree 节点；本机 Hardware Manager 使用带 Vivado cable libraries 的 `hw_server` 仍返回 0 targets；bitstream download、PL DMA、hardware inference 和 30-minute stability 保持 `not_run`

## 首次 FPGA 测试准备状态

- 已准备：KR260/K26 bitstream、XSA、Vivado post-route 报告、寄存器表、runtime/replay model、参数包 checksum。
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
- blocking findings：独立任务 PR、正式 teacher/LIBERO 数据和 KR260 hardware inference bring-up 未完成；当前 checkout 缺少另一台机器生成的最新 Vivado 二进制/日志，板端仍是 starter-kit overlay 且无 JTAG target
- disposition：保留 `in_progress`；gated-fusion 分阶段 co-sim 已通过并归档，软件 gate 已闭合，硬件加载需先取得当前源码对应的 bitstream/XSA 和 root/JTAG 访问

### Follow-up review after board probe and software rerun

- review 时间：2026-09-20（本次工作树增量）
- reviewer：Codex
- review 结果：`PASS_WITH_ACCEPTANCE_GATES`
- structural checks：`git diff --check` 通过；当前增量只修改状态/发布记录、生成 manifest 和测试报告；新增或修改文件均低于 1k 行；Vivado 生成目录不作为源码审查对象
- abstraction/branching checks：manifest 仍由单一生成器负责 artifact/task 状态；没有新增 fallback、板卡分支、重复解析器或跨层状态机
- boundary checks：MVP 路径仍显式依赖 PL executor；board probe 只读且硬件状态保持 `not_run`；软件 replay latency 明确标为本机测量
- validation evidence：`.venv` unit tests 9/9、GEMM/Conv C simulation、fusion/action C simulation、runtime C simulation、replay、1000-cycle safety replay、contract、KR260 block manifest、Vivado baseline 和 ruff 全部通过
- blocking findings/disposition：独立任务 PR、正式 teacher/LIBERO 数据、当前源码 Vivado 构建可复核产物、root/JTAG、TurboVLA bitstream load、PL DMA 和 hardware inference 仍缺失；不以软件报告替代，继续保持 `in_progress`

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
