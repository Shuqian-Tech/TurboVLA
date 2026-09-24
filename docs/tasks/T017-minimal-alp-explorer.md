# T017：最小模块化 ALP 探索、开发与验证框架

- 状态：`in_review`
- Sprint：Sprint 3
- 分支：`task/T017-alp-explorer`
- PR：替代 PR 待创建（原 PR #12 因 `main` 已占用 T016 而被取代）
- 依赖：T009、T010、T013、T015
- 验收 skill：`thermo-nuclear-code-quality-review`
- 开始时间：2026-09-24
- 唯一硬件目标：AMD Kria KR260/K26（`xck26-sfvc784-2LV-c`）
- 硬件 bring-up：`not_run`（框架任务不自动操作开发板）

## 目标

以 `redwood_alp_tech_flow.html` 的 Hardware Loop、Software Loop 和
Local-first Runtime Foundation 为主流程，结合
`fpga_long_horizon_exploration_stack.md` 的不可变设计图、独立 evaluator、事件和
确定性 policy，建立一个可本地运行的最小框架。框架统一编排现有 TurboVLA
contract、软件 reference、HLS/RTL、Vivado 报告、runtime、replay 和 stability
验证，但不复制这些工具的实现。

## MVP 范围

1. 不可变 `DesignState`、`Evaluation`、`Event` 和 agent `Decision` 数据模型；
2. SQLite 单机状态仓库，记录 candidate lineage、evaluation 和事件；
3. 本地内容寻址 artifact store，保存 stdout、stderr 和结果 manifest；
4. 基于 `asyncio`/subprocess 的本地执行器，支持超时、并发上限和显式资源锁；
5. evaluator 注册表和 TurboVLA 现有工具适配，不在框架内实现推理 fallback；
6. ALP 确定性 gate：cheap validation、implementation readiness、promotion 和
   software-loop feedback；
7. CLI：初始化 workspace、创建/派生 candidate、执行 profile、查看状态和事件；
8. 文档分为 `distilled-turbovla-on-fpga` 与 `rtl-design-topo` 两个入口，分别提供
   latest status、Sprint 和 task 索引；原任务文件继续作为唯一状态源。

## 明确不做

- 不在 T017 引入 Ray、PostgreSQL、MinIO、FastAPI、Kubernetes、Temporal 或 MLflow；
- 不自动生成或修改 RTL，不让 LLM 直接执行未校验的 orchestration；
- 不自动加载 bitstream、复位板卡或执行机器人动作；
- 不增加 VPK180、Alveo、Versal、ASIC、DPU、Vitis AI 或 CPU inference fallback；
- 不把既有 Vivado/板端报告重新描述为本次运行结果。

## 计划交付物

- `rtl_design_topo/`：模型、repository、artifact store、executor、evaluator、policy、
  controller 和 CLI；
- `configs/rtl_design_topo_minimal.json`：KR260-only 工具/profile 配置；
- `tests/test_rtl_design_topo.py`：lineage、持久化、artifact、并发执行和 gate 测试；
- `docs/distilled-turbovla-on-fpga/`：现有模型到 FPGA 工作流的导航与状态入口；
- `docs/rtl-design-topo/`：框架架构、Redwood ALP 映射、latest status、Sprint/task
  索引和使用说明。

## 验收标准

- 同一 parent 能创建多个不可变 child candidate，历史节点不能被覆盖；
- evaluator 通过共同接口运行，结果、耗时、退出码、日志引用和 SHA256 可追溯；
- 同成本层 evaluator 可并行，失败不会触发未满足依赖的昂贵阶段；
- policy 只依据结构化结果产生 `continue`、`fork`、`repair`、`promote`、`feedback` 或
  `stop`，agent decision 先经过 schema/boundary 校验；
- smoke profile 能调用仓库已有的 contract、KR260 block manifest 和 Vivado
  baseline validator；
- software profile 能描述现有 C-sim/runtime/replay/stability 验证，但不会静默
  替换为 CPU inference；
- 框架状态、日志和新报告写入显式 workspace/artifact root；existing HLS/Vivado
  evaluator 只使用其已有、已记录的 `build/` 输出路径，不修改 candidate 源文件；
- 单元测试、smoke CLI、`git diff --check` 和 scoped lint/compile 检查通过；
- thermo-nuclear review 覆盖文件大小、抽象、分支、重复逻辑、边界和 findings
  disposition；PR 创建前状态保持 `in_progress` 或 `in_review`。

## 计划验证命令

```bash
PYTHONPATH=. .venv/bin/python -m unittest tests.test_rtl_design_topo -v
PYTHONPATH=. .venv/bin/python -m rtl_design_topo.cli --help
PYTHONPATH=. .venv/bin/python -m rtl_design_topo.cli init --workspace /tmp/turbovla-alp-smoke
PYTHONPATH=. .venv/bin/python -m rtl_design_topo.cli create --workspace /tmp/turbovla-alp-smoke --hypothesis baseline --change-description baseline
PYTHONPATH=. .venv/bin/python -m compileall -q rtl_design_topo tests/test_rtl_design_topo.py
git diff --check
```

## 当前执行记录

- 2026-09-24：任务合同建立后完成 V0 实现；状态进入 `in_review`。
- T017 专项单测：10/10 通过；全仓 `.venv` unittest：45/45 通过。
- `software` profile：8/8 evaluator 通过，policy result 为 `promote`；只表示所选
  profile 通过，不代表任务已发布或硬件重新验收。
- ruff、compileall、文档本地链接和 `git diff --check` 通过。
- 验证证据：[T017 validation](../rtl-design-topo/evidence/t017-validation.md)。
- 软件 Vivado evidence：本次运行既有 report manifest validator 通过；未重新执行
  Vivado synthesis/implementation/bitstream，不冒充新构建。
- 真实硬件：`not_run`；T017 默认禁止 destructive board action。
- 合并最新 `main` 并由 T016 顺延为 T017 后，全仓 45/45 tests、ruff、compileall、
  文档目标、冲突标记和 `git diff --check` 复核通过；框架实现相对 `321d88c` 未变化。

## Changed Files

- `rtl_design_topo/`：领域模型、SQLite、artifact、executor、evaluator、policy、
  controller、source identity 和 CLI；
- `configs/rtl_design_topo_minimal.json`：KR260-only profiles；
- `tests/test_rtl_design_topo.py`：10 个框架测试；
- `docs/distilled-turbovla-on-fpga/`、`docs/rtl-design-topo/`：分域文档；
- `pyproject.toml`：package discovery 与 `turbovla-alp` CLI entry point。

## Thermo-Nuclear Review

- review 时间：2026-09-24
- reviewer：Codex
- review 范围：原 `task/T016-alp-explorer` / PR #12 增量；因 `main` 的 T016 编号冲突，
  合并最新 `main` 后顺延为 `task/T017-alp-explorer`
- review 结果：`PASS_WITH_PR_GATE`；无未处置代码 blocking finding
- 结构/code-judo：使用不可变 design graph、共同 evaluator spec 和单一 controller；
  没有为每个工具复制 runner。审查中将 design/evaluation 与 event 改为同一 SQLite
  事务，将大日志改为流式落盘归档，并用 evaluation ID 隔离输出，删除半状态、内存
  聚合和 stale report 三类风险。
- 文件大小：生产模块最大 199 行，测试文件 269 行；没有文件接近或超过 1,000 行。
- 抽象/分支：依赖 readiness/blocked 逻辑集中在 controller，promotion 逻辑集中在
  policy，Git identity 集中在 source boundary；没有把 tool-specific 条件散落到共享流。
- boundary：config 强制 KR260/K26；expensive evaluator 必须显式 opt-in；agent 不能
  直接 promote；无 DPU、Vitis AI、替代 FPGA target、CPU inference fallback 或自动
  board action。
- finding 1：初版 design/evaluation 与 event 分事务写入。已改成 repository 单事务。
- finding 2：初版 subprocess 在内存聚合日志且 replay 输出复用固定路径。已改成
  流式日志、content-addressed artifact 和 per-evaluation output。
- finding 3：初版 candidate 只记录 HEAD，脏树变化后仍可运行。已增加 dirty fingerprint
  和执行前 identity gate，并覆盖拒绝测试。
- finding 4：初版 replay adapter 使用不合法的 `--repeats 1`。框架正确返回 `repair`，
  配置修正为 2 后完整 profile 通过。
- disposition：上述 findings 全部解决；HLS/Vivado full build 和实机为 `not_run`；
  T017 替代 PR 合并仍是进入 `done` 的流程 gate。

### 最新 main 合并后复核

- review 时间：2026-09-24；reviewer：Codex；结果：`PASS_WITH_PR_GATE`。
- 冲突处置：保留 `main` 已合并的 T016 README 任务，将本框架原子性地顺延为
  T017，并同步任务、Sprint、latest status 和 evidence 路径；没有并存两个 T016。
- 结构/边界：`rtl_design_topo/`、配置、测试和 `pyproject.toml` 相对已审查提交
  `321d88c` 无变化；生产模块最大 199 行，仍无替代硬件目标、CPU inference fallback、
  自动上板或绕过 expensive gate 的路径。
- 验证：全仓 unittest 45/45、T017 专项 10/10、ruff、compileall、链接目标、冲突标记
  和 `git diff --check` 通过；无新增 blocking finding。
