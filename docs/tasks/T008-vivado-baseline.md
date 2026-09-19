# T008：完成综合、布局布线和报告基线

- 状态：`planned`
- Sprint：Sprint 2
- 分支：`task/T008-vivado-baseline`
- PR：待创建
- 依赖：T007
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务要求

在 KR260 上完成 Vivado synthesis、implementation、post-route timing 和 bitstream/XSA 生成，建立第一个资源、时序、功耗和带宽 baseline。

## 交付物

- bitstream；
- XSA；
- utilization、timing、power、CDC 和 congestion reports；
- 构建日志和 git commit manifest。

## 详细验收

- post-route timing 无 violation；
- clock/reset/CDC 报告无未解释错误；
- 资源使用率和 DDR 带宽在项目阈值内；
- 构建可由 Tcl 从干净目录重现；
- thermo-nuclear review 确认报告归档和工程目录没有巨型脚本或临时条件分支；
- PR 链接所有报告并记录风险。
