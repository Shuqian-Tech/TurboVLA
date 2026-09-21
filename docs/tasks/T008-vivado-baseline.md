# T008：完成综合、布局布线和报告基线

- 状态：`in_progress`
- Sprint：Sprint 2
- 分支：`task/T008-vivado-baseline`
- PR：待创建
- 依赖：T007
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T008-vivado-baseline`
- report template：`hardware/vivado_kr260/report_manifest.template.json`
- report archive：`hardware/vivado_kr260/reports/`
- validator：`tools/validate_vivado_baseline.py`
- 当前状态：当前源码对应的 KR260/K26 baseline 已重新归档；结果 manifest 标记 `current_source_verified`
- 硬件 bring-up：`not_run`

## 验证记录

- `python3 tools/validate_vivado_baseline.py hardware/vivado_kr260/report_manifest.json`：通过
- 默认校验会拒绝模板的 `not_run` timing/utilization/power/CDC 状态：符合 T008 门禁
- `ruff check tools/validate_vivado_baseline.py`：通过
- `/home/frank/AMD/vivado/2025.01/2025.1/Vivado/bin/vivado -version`：通过（v2025.1）；离线 Kria device package 已补齐
- `vivado -mode batch -source hardware/vivado_kr260/build.tcl -nolog -nojournal -notrace`：当前源码通过；完整日志：`/tmp/turbovla-vivado-current.log`
- bitstream、XSA、post-route timing、utilization、power、CDC：当前源码通过；WNS `3.476 ns`、TNS `0`、WHS `0.010 ns`、THS `0`、power `2.741 W`、CDC critical `0`
- 当前源码全量 Vivado 重建：通过；日志 `/tmp/turbovla-vivado-current.log`；生成 `hardware/vivado_kr260/build/turbovla_kr260.bit` 与 `turbovla_kr260.xsa`
- 当前源码 post-route 结果：WNS `3.476 ns`、TNS `0`、WHS `0.010 ns`、THS `0`、power `2.741 W`、CDC critical `0`；资源为 LUT `19.88%`、FF `13.25%`、DSP `2.00%`、BRAM `5.21%`、URAM `0%`

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_PR_GATE`
- 结构检查：报告模板、归档说明和 validator 分离；无巨型 Tcl 或临时条件分支
- code-judo 检查：同一 manifest 同时承载平台、artifact、timing、资源和 power 门禁，避免多个互相漂移的阈值文件
- blocking findings：无代码 blocking finding；gated-fusion RTL co-sim 和板端 bring-up 仍未完成
- disposition：回到 `in_progress`，当前源码的软件 Vivado gate 已闭合，等待独立 PR、co-sim 资源问题处理和硬件 bring-up

## 任务要求

使用 KR260/K26 目标器件的 Vivado 软件工程完成 synthesis、implementation、post-route timing 和 bitstream/XSA 生成，建立第一个资源、时序、功耗和带宽 baseline；不要求开发板在线。

## 交付物

- bitstream；
- XSA；
- utilization、timing、power、CDC 和 congestion reports；
- 构建日志和 git commit manifest。

## 详细验收（software_only）

- post-route timing 无 violation；
- clock/reset/CDC 报告无未解释错误；
- 资源使用率和 DDR 带宽在项目阈值内；
- 构建可由 Tcl 从干净目录重现；
- 报告明确标记 `software_only`，Hardware Manager/JTAG 为 `not_run`；
- thermo-nuclear review 确认报告归档和工程目录没有巨型脚本或临时条件分支；
- PR 链接所有报告并记录风险。
