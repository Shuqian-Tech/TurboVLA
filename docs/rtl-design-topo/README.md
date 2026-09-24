# RTL Design Topology

这是以 Redwood ALP Hardware Loop / Software Loop 为主流程的本地优先探索框架。
它把 TurboVLA 已有工具包装成独立 evaluator，用不可变 candidate 图、结构化 evidence、
确定性 gate 和内容寻址 artifact 将“提出候选、开发、验证、晋级、反馈”连成一个闭环。

## 导航

- [Latest status](latest-status.md)
- [架构与模块边界](architecture.md)
- [ALP 节点映射](alp-flow-mapping.md)
- [T017 验证证据](evidence/t017-validation.md)
- [Sprint 索引](sprints/README.md)
- [Task 索引](tasks/README.md)
- [Redwood ALP 原始流程](../../redwood_alp_tech_flow.html)
- [项目工具映射 HTML](../../redwood_alp_project_tool_mapping.html)
- [长周期探索设计参考](../../fpga_long_horizon_exploration_stack.md)

## 快速使用

```bash
export ALP_WORKSPACE=/tmp/turbovla-alp
PYTHONPATH=. .venv/bin/python -m rtl_design_topo.cli init --workspace "$ALP_WORKSPACE"
PYTHONPATH=. .venv/bin/python -m rtl_design_topo.cli create \
  --workspace "$ALP_WORKSPACE" \
  --hypothesis baseline \
  --change-description "current checked-out design"
```

默认要求工作树干净，使 candidate 可由 commit 重现。需要探索尚未提交的修改时，
显式添加 `--allow-dirty`；框架会记录 dirty 标记和工作树内容指纹，但正式晋级仍应使用
已提交 revision。用 `fork --parent-design-id <design_id>` 创建不可变 child candidate。

`create` 会输出 `design_id`。使用该 ID 执行便宜的确定性 gate：

```bash
PYTHONPATH=. .venv/bin/python -m rtl_design_topo.cli run \
  --workspace "$ALP_WORKSPACE" \
  --design-id <design_id> \
  --profile smoke
```

`full-vivado` 包含 HLS/Vivado 长时间任务，必须显式添加 `--allow-expensive`。
框架没有自动上板命令；板卡操作保持人工、非破坏性和独立证据记录。
