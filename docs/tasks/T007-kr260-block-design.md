# T007：搭建 KR260 Vivado Block Design

- 状态：`in_progress`
- Sprint：Sprint 2
- 分支：`task/T007-kr260-block-design`
- PR：待创建
- 依赖：T005、T006
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T007-kr260-block-design`
- 工程：`hardware/vivado_kr260/build.tcl`、`create_block_design.tcl`、`constraints.xdc`
- 静态 contract：`hardware/vivado_kr260/register_map.json`
- 目标器件：唯一目标 `xck26-sfvc784-2LV-c`（KR260/K26）
- fail-fast 边界：T005/T006 packaged IP 缺失时 Tcl 直接报错，不创建 CPU fallback 或空 kernel
- 硬件 bring-up：`not_run`

## 验证记录

- `python3 tools/validate_kr260_block_manifest.py`：通过，15 registers
- register offset 与 T001 contract：一致且 4-byte 对齐
- DMA buffer alignment：全部 64-byte
- `vivado -version`：未通过，wrapper 指向不存在的 `/home/frank/AMDDesignTools/2026.1/Vivado/bin/vivado`
- block design validation、synthesis、XSA/bitstream：`not_run`，不能把静态 manifest 当作 Vivado 结果

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_TOOLCHAIN_GATE`
- 结构检查：project Tcl、block design Tcl、约束和 register manifest 分层；无 board-specific if/else 分支
- code-judo 检查：register map 只维护一份静态映射，validator 对照 T001 contract，不复制 runtime offsets
- blocking findings：无代码 blocking finding；缺少 Vivado/IP repository 工具验证
- disposition：保留 `in_progress`，工具恢复并完成 IP packaging 后补齐 validation/report

## 任务要求

建立仅面向 KR260/K26 的 Vivado block design，连接 Zynq UltraScale+ PS、DDR、AXI SmartConnect、AXI DMA、AXI-Lite scheduler、kernel IP 和 interrupt controller。

## 交付物

- block design Tcl；
- Vivado project/build Tcl；
- XDC/clock/reset 约束；
- register map；
- XSA 和 block design validation log。

## 详细验收（software_only）

- 只引用 KR260/K26 平台；
- block design validation 通过；
- DMA buffer、cache policy、stride、interrupt 和 reset 行为有文档；
- synthesis 可以非交互执行；
- 软件 Vivado 使用 KR260/K26 目标器件完成 block design validation，不要求开发板或 Hardware Manager；
- Hardware Manager/JTAG 状态记录为 `not_run`，不得用仿真日志冒充实机连接；
- thermo-nuclear review 确认平台选择和控制逻辑没有散落的 board-specific if/else；
- PR 附带 project version、Vivado version 和构建命令；若 Vivado 不可执行，记录工具环境 blocker。
