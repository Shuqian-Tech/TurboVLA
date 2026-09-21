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
- 当前状态：本机已从当前源码重建 KR260/K26 software-only baseline；仍无实机加载证据
- 硬件 bring-up：`not_run`

## 验证记录

- `python3 tools/validate_vivado_baseline.py hardware/vivado_kr260/report_manifest.json`：通过
- 默认校验会拒绝模板的 `not_run` timing/utilization/power/CDC 状态：符合 T008 门禁
- `ruff check tools/validate_vivado_baseline.py`：通过
- `vivado -version`：通过，wrapper 已指向 `/home/frank/AMDDesignTools/2025.1/2025.1/Vivado/bin/vivado`（v2025.1）
- `vivado -mode batch -source hardware/vivado_kr260/build.tcl -nolog -nojournal -notrace`：通过；完整日志：`/tmp/turbovla-vivado-build-final.log`
- bitstream、XSA、post-route timing、utilization、power、CDC：通过；WNS `3.512 ns`、TNS `0`、WHS `0.010 ns`、THS `0`、power `2.742 W`、CDC critical `0`
- 当前源码本机重建：`/tmp/turbovla-current-build.3zY7TN/vivado-current.log` 返回 0；synthesis、implementation、post-route、bitstream、XSA 通过，WNS `3.476 ns`、TNS `0`、WHS `0.010 ns`、THS `0`；LUT `19.88%`、FF `13.25%`、DSP `2.00%`、BRAM `5.21%`、URAM `0%`；功耗估算 `2.741 W`
- 本次软件时钟 `clk_pl_0=96.974 MHz`，不能据此宣称 200 MHz；功耗为 medium-confidence vectorless 估算并提示 reset 活动可能影响精度；CDC 报告未列 crossing 违规，但未约束输入端口被跳过
- bitstream SHA256 `c31f375d5f604d3fb57c890c986665e6a05f1f5d2c3749140f8f90dde9e2a2c6`；XSA SHA256 `7566e039aa4776f43d41509c34def2129338026d93a9caf48b40aeae13282438`

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_PR_GATE`
- 结构检查：报告模板、归档说明和 validator 分离；无巨型 Tcl 或临时条件分支
- code-judo 检查：同一 manifest 同时承载平台、artifact、timing、资源和 power 门禁，避免多个互相漂移的阈值文件
- blocking findings：无代码 blocking finding；本机当前源码 Vivado 重建已完成，但仅在 `96.974 MHz` 下有 post-route 正余量；200 MHz 目标、实机 bring-up 和独立任务 PR 尚未运行
- disposition：保持 `in_progress`，本地软件构建证据通过但不替代板端或 PR gate

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
