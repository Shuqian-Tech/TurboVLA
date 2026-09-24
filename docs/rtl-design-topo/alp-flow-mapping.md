# Redwood ALP 到最小框架的映射

| ALP 流程节点 | V0 框架模块 | TurboVLA 实际工具 | V0 状态 |
|---|---|---|---|
| Architecture / microarchitecture spec | `DesignState.constraints` + config | JSON contract、Git、task docs | 已接入 |
| Architecture Search | parent/child design graph | 人工/Codex 提出 hypothesis | 最小接入 |
| Performance Model | evaluator 扩展点 | 当前无 pre-RTL model | 没有 |
| Worth RTL Implementation | `AlpPolicy` cheap gate | contract 和基础验证 | 最小接入 |
| Generate RTL Candidate | Git revision + child node | task branch / agent edit | 外部执行 |
| Performance Simulator | evaluator 扩展点 | 当前主要为 HLS/XSIM，不是完整 perf simulator | 部分 |
| Verification Closure | evaluator profile | unittest、HLS C-sim、XSIM | 已接入接口 |
| Physical Search | evaluator profile | 固定 Vivado synthesis/implementation | 部分 |
| N1 diagnosis / Fix RTL | failed evidence + `repair` decision | Codex/人工分析日志 | 最小接入 |
| Candidate Manager | `ExplorationController` + SQLite | 新增 | 已实现 |
| Evaluation Barrier | dependency graph + policy | 结构化 exit status | 已实现 |
| FPGA Build Queue | resource semaphore | `vivado=1` 本地串行资源 | 最小接入 |
| FPGA Build Service | explicit-only evaluator | Vitis HLS + Vivado Tcl | 已接入接口 |
| Board Manager / Pool | 无 | 现有手工 KR260 流程 | V0 不实现 |
| Existing FPGA Build | artifact/evidence reference | T013/T015 bitstream/package/runtime | 引用既有证据 |
| Firmware / Kernel Search | software profile 扩展点 | PS C++ runtime，无自动搜索 | 部分 |
| Run Workload on FPGA | 无自动命令 | KR260 XRT/UIO runtime | V0 不自动执行 |
| Bottleneck Analyzer | event/policy 扩展点 | 当前人工报告分析 | 没有 |
| Persistent State | `SqliteRepository` + Git | 新增本地 SQLite | 已实现 |
| Artifact Store | `ArtifactStore` | 本地 filesystem + SHA256 | 已实现 |
| Tool Gateway | config + evaluator registry + CLI | Python CLI | 最小接入 |
| Resource Manager | named `asyncio.Semaphore` | CPU/XSIM/Vivado capacity | 最小接入 |

完整的 35 节点静态盘点见
[Redwood ALP 与 TurboVLA 工具映射](../../redwood_alp_project_tool_mapping.html)。
