# T012：最终 thermo-nuclear 审查与发布归档

- 状态：`planned`
- Sprint：Sprint 3
- 分支：`task/T012-final-acceptance`
- PR：待创建
- 依赖：T008、T009、T010、T011
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务要求

对当前 MVP 分支和全部任务 PR 做最终结构、可维护性、边界、Vivado 工程和 runtime 归档审查。该任务是发布门，不是简单的文档整理。

## 交付物

- thermo-nuclear review report；
- 所有任务 PR/commit 清单；
- bitstream、XSA、参数包和 checksum；
- Vivado/HLS/功能/稳定性报告索引；
- 最终开发状态更新。

## 详细验收

- 完整执行 skill 中的 code-judo、文件大小、抽象、分支、边界和重复逻辑检查；
- 所有阻塞 findings 已解决或由项目 owner 书面豁免；
- 仅 KR260/K26 目标相关工程进入发布归档；
- 没有 DPU、Vitis AI 或 CPU inference fallback；
- 所有任务文件状态、Sprint 状态和 `docs/development_status.md` 一致；
- PR 合并前由 reviewer 明确写出 `accepted` 或 `blocked`，不得只写“looks good”。
