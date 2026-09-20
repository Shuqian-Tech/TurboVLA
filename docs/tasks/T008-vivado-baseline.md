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
- 当前状态：模板通过 `--allow-not-run` 静态校验；真实 synthesis/implementation/post-route 尚未执行
- 硬件 bring-up：`not_run`

## 验证记录

- `python3 tools/validate_vivado_baseline.py hardware/vivado_kr260/report_manifest.template.json --allow-not-run`：通过
- 默认校验会拒绝模板的 `not_run` timing/utilization/power/CDC 状态：符合 T008 门禁
- `ruff check tools/validate_vivado_baseline.py`：通过
- `vivado -version`：失败，wrapper 指向不存在的 `/home/frank/AMDDesignTools/2026.1/Vivado/bin/vivado`
- bitstream、XSA、post-route timing、utilization、power、CDC：`not_run`

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_TOOLCHAIN_GATE`
- 结构检查：报告模板、归档说明和 validator 分离；无巨型 Tcl 或临时条件分支
- code-judo 检查：同一 manifest 同时承载平台、artifact、timing、资源和 power 门禁，避免多个互相漂移的阈值文件
- blocking findings：无代码 blocking finding；Vivado 工具不可用，无法生成真实报告
- disposition：保留 `in_progress`，恢复工具后运行 `build.tcl` 并替换模板值

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
