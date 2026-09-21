# TurboVLA 纯 FPGA 的 Vivado 实现与编译流程

## 1. 工具边界

本项目不使用 Vitis AI/DPU。推荐的工具链边界如下：

```text
Python/PyTorch reference
        |
        v
固定 shape、定点化和校准数据
        |
        v
HLS C++ kernel 或手写 RTL
        |
        v
Vivado IP Integrator
  PS + DDR + AXI DMA + accelerator IP
        |
        v
Vivado synthesis -> implementation -> bitstream
        |
        v
PetaLinux/Ubuntu runtime + C++/ROS2 driver
```

Vitis HLS 可以用来把 GEMM、attention、LayerNorm 等 C++ kernel 生成为 RTL IP；最终的系统集成、综合、布局布线、时序分析和 bitstream 生成仍由 Vivado 完成。若直接手写 Verilog/SystemVerilog，则跳过 HLS，直接封装为 Vivado IP。

## 2. 代码如何拆分

不要把整个 TurboVLA 写成一个超大的顶层模块。建议每个硬件算子都有独立的输入、输出和控制接口：

```text
hardware/
  rtl/common/
    axis_fifo.sv
    fixed_point.sv
    stream_utils.sv
  hls/gemm/
    gemm.cpp
    gemm.h
  hls/attention/
    qkv_projection.cpp
    online_softmax.cpp
    attention.cpp
  hls/norm/
    layernorm.cpp
    gelu.cpp
  rtl/control/
    turbovla_scheduler.sv
  vivado_kr260/
    block_design.tcl
    constraints.xdc
    build.tcl
```

第一版应只实现一个可复用 GEMM IP、一个 attention IP 和一个 LayerNorm IP，再通过 scheduler 按层调度。不要给 DINOv3 的每层复制完整计算阵列。

## 3. Kernel 编写约束

HLS kernel 必须使用固定 shape 或有限的参数集合，避免动态内存和不可综合的 C++ 特性：

- 不使用 `malloc`、递归、异常、虚函数和 STL 容器；
- 数组尺寸在编译期确定，或通过受限模板参数确定；
- AXI4-MM 用于 DDR，AXI4-Stream 用于 kernel 间高速传输；
- 控制参数通过 AXI4-Lite 暴露；
- 计算使用定点类型或明确位宽的整数类型；
- 累加器使用比输入更宽的类型，INT8 GEMM 至少使用 INT32 累加；
- 输入和输出 buffer 使用双缓冲，保证 DMA 与计算重叠。

典型 GEMM kernel 应包含以下 HLS 优化方向：

```cpp
#pragma HLS DATAFLOW
#pragma HLS ARRAY_PARTITION variable=a_tile complete dim=2
#pragma HLS ARRAY_PARTITION variable=b_tile complete dim=1
#pragma HLS PIPELINE II=1
#pragma HLS UNROLL factor=<synthesis-tuned-factor>
```

这些 directive 不能盲目添加。每次修改后都要检查 initiation interval、DSP、BRAM、URAM、LUT、FF 和时序报告；如果 unroll 造成资源爆炸或 routing congestion，应降低并行因子。

## 4. Vivado Block Design

KR260 的系统顶层建议包含：

```text
Zynq UltraScale+ MPSoC PS
  ├── DDR controller
  ├── AXI SmartConnect
  ├── AXI4-Lite -> scheduler / kernel registers
  ├── AXI DMA 或自定义 AXI master
  ├── GEMM IP
  ├── Attention IP
  ├── LayerNorm/GELU/softmax IP
  └── interrupt controller -> PS
```

大数据走 PS 到 DDR 的高性能 AXI 端口；控制和状态走 AXI4-Lite；连续 token 数据优先走 AXI4-Stream。每个 kernel 要有明确的 buffer ownership、cache policy、stride 和 tensor layout，避免运行时再做大规模 transpose。

## 5. Vivado 编译和优化顺序

当前阶段采用软件验证模式。KR260 开发板、SSH 和 Vivado Hardware Manager 不参与 T001-T008 的通过条件；Vivado 仍然以 KR260/K26 目标器件完成完整的离线工程验证。任何报告必须标明 `software_only`，不能写成实机测量。

建议使用非交互 Tcl flow，保证每次构建可复现：

```text
1. 创建 KR260 Vivado project 或导入固定 board/platform
2. 创建/更新 HLS IP
3. 运行 IP packaging
4. 运行 block design Tcl
5. 生成 output products
6. 综合 synthesis
7. 查看 utilization、power、clock 和 synthesis timing
8. 实现 implementation
9. 查看 placement、routing、congestion 和 post-route timing
10. 生成 bitstream
11. 导出 hardware handoff / XSA
12. 在目标系统加载 bitstream 并运行 runtime driver
```

第 12 步属于后续 hardware bring-up，不是当前软件 MVP 的必要步骤。当前软件验收到第 10/11 步即可，但必须保存 bitstream/XSA 生成日志，并把硬件 bring-up 状态记录为 `not_run`。

优化顺序应是：

1. 先保证 C simulation 与 PyTorch reference 正确；
2. 再保证 HLS C/RTL co-simulation 正确；
3. 再以目标时钟运行综合和实现；
4. 根据报告调整 tile size、unroll factor、buffer 深度和 AXI burst；
5. 最后才做跨 kernel dataflow 和时钟域优化。

不要只看 synthesis timing。KR260 最终必须看 post-route timing，因为 attention 和大规模 GEMM 的布线拥塞可能在布局布线阶段才暴露。

## 6. 必须保存的构建报告

每次硬件构建至少保存：

- HLS latency、II、loop trip count 和资源报告；
- Vivado utilization report；
- post-synthesis timing summary；
- post-route timing summary；
- clock interaction 和 CDC report；
- power estimate；
- bitstream、XSA、硬件版本号和 git commit；
- FP32/定点逐层误差报告。

建议使用以下目录保存结果：

```text
build/
  vivado/<timestamp>/
  hls/<timestamp>/
  reports/<timestamp>/
  artifacts/<timestamp>/
```

## 7. 第一版不要做的事情

- 不要把完整 TurboVLA 一次性写成一个 monolithic HLS top；
- 不要先做 RoboTwin 三视角版本；
- 不要一开始使用全 FP32；
- 不要依赖 CPU fallback 来掩盖未实现的算子；
- 不要在没有 post-route timing 的情况下宣称达到目标频率或帧率。

第一版软件验证应以“单个 GEMM/attention/LayerNorm IP 可综合、可布局布线、post-route timing 通过、资源/功耗/CDC 报告齐全并与软件 reference 对齐”为完成标准。PS 实机读写属于后续 hardware bring-up，不得用软件仿真结果冒充。
