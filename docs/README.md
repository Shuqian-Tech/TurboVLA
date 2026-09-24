# TurboVLA 文档域

本仓库的文档分为两个相互关联、边界明确的域：

| 文档域 | 关注内容 | 入口 |
|---|---|---|
| Distilled TurboVLA on FPGA | TinyCNN student、量化、HLS、Vivado、KR260 runtime 与闭环证据 | [进入](distilled-turbovla-on-fpga/README.md) |
| RTL Design Topology | 以 Redwood ALP 为核心的候选设计图、探索、执行和验证框架 | [进入](rtl-design-topo/README.md) |

## 状态源规则

- 项目总状态仍以 [development_status.md](development_status.md) 为唯一来源；
- Sprint 状态仍以 [sprint/](sprint/README.md) 为唯一来源；
- 任务合同仍以 [tasks/](tasks/README.md) 为唯一来源；
- 两个文档域中的 `latest-status`、`sprints` 和 `tasks` 是分域导航，不复制或覆盖任务状态。

这样可以按主题浏览，同时避免同一个任务在多个目录中形成互相冲突的状态副本。
