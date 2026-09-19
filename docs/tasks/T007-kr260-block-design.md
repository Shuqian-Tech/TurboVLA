# T007：搭建 KR260 Vivado Block Design

- 状态：`planned`
- Sprint：Sprint 2
- 分支：`task/T007-kr260-block-design`
- PR：待创建
- 依赖：T005、T006
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务要求

建立仅面向 KR260/K26 的 Vivado block design，连接 Zynq UltraScale+ PS、DDR、AXI SmartConnect、AXI DMA、AXI-Lite scheduler、kernel IP 和 interrupt controller。

## 交付物

- block design Tcl；
- Vivado project/build Tcl；
- XDC/clock/reset 约束；
- register map；
- XSA 和 block design validation log。

## 详细验收

- 只引用 KR260/K26 平台；
- block design validation 通过；
- DMA buffer、cache policy、stride、interrupt 和 reset 行为有文档；
- synthesis 可以非交互执行；
- thermo-nuclear review 确认平台选择和控制逻辑没有散落的 board-specific if/else；
- PR 附带 project version、Vivado version 和构建命令。
