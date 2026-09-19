# T001：冻结 MVP 模型与接口契约

- 状态：`in_progress`
- Sprint：Sprint 1
- 分支：`task/T001-freeze-mvp-contract`
- PR：待创建
- 依赖：无
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T001-freeze-mvp-contract`
- KR260 SSH：`ubuntu@192.168.68.123`，待执行只读连通性验证
- Hardware Manager：用户已确认已连接，待硬件任务开始前验证 active target/device
- PR：尚未创建

## 验证记录

- `python3 tools/validate_mvp_contract.py`：通过，输出 `validated hardware/contracts/turbovla_lite_contract.json`
- `ssh -o BatchMode=yes -o ConnectTimeout=5 ubuntu@192.168.68.123 'printf KR260_SSH_OK'`：通过，返回 `KR260_SSH_OK`
- `python tools/validate_mvp_contract.py`：未执行，当前环境没有 `python` 命令；改用 `python3`
- `vivado -version`：阻塞，仓库 wrapper 指向不存在的 `/home/frank/AMDDesignTools/2026.1/Vivado/bin/vivado`
- Hardware Manager active target/device：未在当前 shell 验证；用户已确认连接，硬件任务启动前必须在 Vivado Hardware Manager 中复核

## Thermo-Nuclear Review

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_ENVIRONMENT_BLOCKER`
- 结构检查：contract、文档和校验脚本按边界分离；没有新增超过 1k 行文件；没有散落的 feature flags、CPU fallback 或 board 分支
- code-judo 检查：使用单一 JSON contract 作为 tensor/register/quantization source of truth，避免后续 kernel/runtime 重复定义
- 类型/边界检查：固定 dtype、shape、stride、buffer ownership、错误码和 contract version encoding 已明确
- 阻塞项：Vivado 本地安装路径无效；不影响 T001 contract 验证，但阻塞后续硬件综合任务
- 结论：T001 可进入 `in_review`，待独立 PR 创建并由 reviewer 确认后才能 `accepted/done`

## 任务要求

冻结 TurboVLA-Lite 的输入、输出、instruction ID、tensor layout、量化格式、action normalization、寄存器接口和错误语义。禁止在后续 kernel 开发中通过隐式 reshape 或临时 scale 改变契约。

## 交付物

- 模型配置文件；
- tensor contract 文档；
- instruction ID 表格式；
- action/state normalization 定义；
- DMA buffer layout 和 AXI-Lite register map 草案。

## 详细验收

- 固定 shape 在 Python 中可构造；
- 每个输入/输出 tensor 有 dtype、shape、stride 和 ownership；
- 每个量化 tensor 有 scale、zero point 或明确的对称定点规则；
- instruction ID 越界、state 维度错误和图像尺寸错误都有定义行为；
- 运行 thermo-nuclear review，确认没有用零散 flags 代替清晰的数据契约；
- PR 中附上 contract diff 和 review 记录。
