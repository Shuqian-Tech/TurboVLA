# 最小 ALP 探索框架架构

## 核心闭环

```text
Architecture Spec / Hypothesis
             |
             v
      Immutable DesignState
             |
             v
   Evaluator dependency graph
   | contract / C-sim / XSIM
   | Vivado reports / runtime
   | replay / stability
             |
             v
      Structured Evidence
             |
             v
 Deterministic ALP Policy Gate
   | continue | repair | promote
             |
             v
       Child DesignState
```

## 模块边界

| 模块 | 责任 | 后续可替换为 |
|---|---|---|
| `models.py` | Design、Evaluation、Event、Decision schema | 稳定领域合同，不替换 |
| `repository.py` | 单机状态与 lineage | PostgreSQL repository |
| `artifacts.py` | 日志和结果内容寻址存储 | MinIO/S3 |
| `evaluators.py` | 工具描述、profile 和依赖校验 | 动态 tool registry |
| `executor.py` | 本地异步进程、timeout、资源锁 | Ray executor |
| `policy.py` | 确定性 readiness/promotion gate | 扩展预算/Pareto policy |
| `controller.py` | 编排 evidence，不解释工具日志 | 分布式 controller |
| `cli.py` | 本地操作界面 | FastAPI/MCP gateway |

## 安全与真实性边界

- 配置加载时拒绝非 `kr260-k26` / `xck26-sfvc784-2LV-c` 目标；
- agent 只能建议 `continue`、`repair` 或 `stop`，不能直接 `promote`；
- agent 可建议 `fork`，但 child 仍由 controller 校验 parent 和 source state 后创建；
- evaluator 退出码决定 pass/fail，LLM 文本不能覆盖工具结果；
- 依赖失败后下游 expensive evaluator 标记 `skipped`；
- stdout/stderr 保存 SHA256 和路径，不塞进 SQLite；
- 大日志直接流式写盘后归档，不在 controller 内存中聚合；声明输出按 evaluation ID 隔离；
- `full-vivado` 需要显式 opt-in；
- 不提供 bitstream load、reset 或机器人动作命令。
- CLI 默认拒绝脏工作树；显式允许时记录 dirty fingerprint，正式晋级仍要求 Git revision。
- 每次 profile 启动前重新校验 HEAD 与 fingerprint；源树变化时必须创建或 fork 新 candidate。

## Candidate 不可变性

一个修改产生新的 child，而不是覆盖 parent：

```text
D0 baseline
|- D1 pipeline experiment
|- D2 buffer-depth experiment
`- D3 quantization experiment
```

SQLite 只追加 design；evaluation 和 event 分别关联 `design_id`。源代码仍由 Git
revision/branch 管理，框架不会在 candidate 源树内自动写文件。
