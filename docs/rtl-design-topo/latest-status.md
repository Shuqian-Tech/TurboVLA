# RTL Design Topology Latest Status

- 更新时间：2026-09-24
- 当前任务：[T016 最小模块化 ALP 探索、开发与验证框架](../tasks/T016-minimal-alp-explorer.md)
- 状态：`in_review`
- 分支：`task/T016-alp-explorer`
- 实现阶段：本地 V0
- 目标：KR260/K26 only
- 板端执行：`not_run`，默认不提供 destructive board action

## V0 能力

- 不可变 design graph 与 parent/child lineage；
- SQLite evaluation/event state；
- 本地内容寻址 artifact store；
- asyncio subprocess executor 与资源 semaphore；
- 配置驱动 evaluator/profile；
- cheap-before-expensive ALP gate 和依赖失败阻断；
- agent decision schema，禁止 agent 直接绕过 promotion gate；
- TurboVLA contract、block manifest、Vivado baseline、C-sim、runtime、replay 和
  stability 适配。

验证结果见 [T016 validation evidence](evidence/t016-validation.md)：全仓 45 tests、
T016 专项 10 tests、software profile 8/8 evaluator 和 thermo-nuclear review 已通过；
独立 PR 尚待创建。

## 延后能力

Ray、PostgreSQL、MinIO/S3、FastAPI/MCP、自动 RTL 生成、board pool、Kubernetes、
MLflow 和 Temporal 均不属于 V0。

权威项目状态：[docs/development_status.md](../development_status.md)。
