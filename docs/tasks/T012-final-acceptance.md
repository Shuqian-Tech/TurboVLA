# T012：最终 thermo-nuclear 审查与发布归档

- 状态：`in_progress`
- Sprint：Sprint 3
- 分支：`task/T012-final-acceptance`
- PR：待创建
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

- 全仓 Python unit tests：通过，9 tests
- T005 GEMM/Conv C simulation：通过
- T006 fusion/action C simulation：通过
- T009 runtime C simulation：通过
- T010 deterministic replay：通过
- T011 1000-cycle safety replay：通过
- `ruff`：新增 Python 文件通过
- Vitis HLS C simulation（T005/T006）：通过；GEMM/Conv/action RTL co-sim：通过；gated-fusion RTL co-sim：deferred；归档 Vivado baseline 通过但早于 `tanh_q15` 修正，当前源码全量重建待另一台机器执行；Hardware Manager/JTAG/hardware inference：`not_run`
- 独立 PR：新 upstream 已配置，任务 PR 仍待创建

## Thermo-Nuclear Review

- review 时间：2026-09-20
- reviewer：Codex
- review 结果：`BLOCKED_BY_ACCEPTANCE_GATES`
- 结构/文件大小/抽象/分支/边界检查：无新增代码 blocking finding；GEMM、fusion/action、runtime、replay、safety 和 manifest 边界清晰
- code-judo 检查：T005 GEMM 被 T006 复用；contract/register map/manifest 避免重复 shape、offset 和 checksum 定义
- 本次增量检查（当前 `task/T012-final-acceptance` 分支与工作树 diff）：HLS launcher 61 行，两个 kernel Tcl 分别覆盖 GEMM/1x1 Conv 与 gated fusion/action MLP solution；无源码文件超过 1k 行，无新增 fallback 或散落的板卡分支
- 审查 finding：`tanh_q15` 的负小数区间最初受 C++ 向零整除影响；已改为显式 floor 区间并增加 `-1.5/+1.5` 回归用例，`python3 tools/run_fusion_action_csim.py` 通过
- blocking findings：独立任务 PR、正式 teacher/LIBERO 数据、gated-fusion RTL co-sim、当前源码 Vivado 全量重建和 KR260 hardware inference bring-up 未完成
- disposition：保留 `in_progress`；低内存软件/HLS gate 已通过，重型 Vivado gate 交接到另一台机器，不把旧 baseline 写成当前源码通过

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
