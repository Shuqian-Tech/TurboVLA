# Sprint 1：最小 ALP 本地闭环

- 状态：`in_review`
- 开始时间：2026-09-24
- 平台：KR260/K26 only
- 项目级关联：[Sprint 3](../../sprint/sprint-3-runtime-acceptance.md)

## 任务

- [T016：最小模块化 ALP 探索、开发与验证框架](../../tasks/T016-minimal-alp-explorer.md)

## 目标

- parent candidate 可产生多个不可变 child；
- existing TurboVLA validators 可作为 evaluator 执行；
- cheap gate 失败时阻断 HLS/Vivado 昂贵阶段；
- evidence、event、artifact 和 decision 可追溯；
- smoke profile 在单机完成，无需服务端依赖。

## 退出条件

- T016 单元测试和 smoke CLI 通过；
- 文档域、latest status、Sprint/task 导航完整；
- thermo-nuclear review 无未处置 blocking finding；
- 独立 PR 已创建后才能按项目规则进入 `done`。
