# TurboVLA-Lite 验收审查

审查日期：2026-09-20
审查者：Codex
目标：仅 AMD Kria KR260/K26
验证模式：`software_only`

## Result

`BLOCKED_BY_ACCEPTANCE_GATES`

软件路径已有确定性 reference、student smoke training、参数包导出、portable/Vitis HLS C simulation、runtime model、replay 和 safety replay 证据。当前源码对应的 KR260/K26 Vivado post-route baseline、bitstream 和 XSA 已重新生成。项目仍不能标记为 `accepted` 或 `done`，因为独立任务 PR 尚未全部创建、正式 teacher/LIBERO 训练数据缺失、gated-fusion RTL co-sim 延期，且硬件 bring-up 仍为 `not_run`。

## Thermo-Nuclear Review

- 没有新增文件超过 1k 行拆分门槛。
- T005/T006 复用 T005 GEMM 核心；fusion/action 没有重复 MAC 实现。
- tensor/register 所有权仍集中在 T001 contract 及 KR260 register-map validator。
- runtime、safety、replay 和报告生成边界明确；没有加入 CPU inference fallback。
- 剩余阻塞是环境或缺失证据门，不是被豁免的代码 finding。

## Evidence

机器可读 artifact 和任务状态索引为 `docs/release/turbovla_lite_release_manifest.json`。软件检查包括 Python 单测、`g++ -Werror` C simulation、Vitis HLS C simulation、ruff、contract/register-map validation、deterministic replay 和 1000-cycle safety replay。当前源码的 Vivado synthesis、implementation、post-route timing、bitstream/XSA、utilization、power 和 CDC 已在 software-only 模式通过；Hardware Manager、bitstream load、hardware inference 和 KR260 30 分钟稳定性仍为 `not_run`。gated-fusion RTL co-sim 在 0/2 事务处持续增长到约 24 GiB RSS 后停止，未计为通过。
