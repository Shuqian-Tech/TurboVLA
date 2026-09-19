# T005：实现 INT8 GEMM/Conv IP

- 状态：`planned`
- Sprint：Sprint 2
- 分支：`task/T005-gemm-conv-ip`
- PR：待创建
- 依赖：T004
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务要求

使用 HLS C++ 或 SystemVerilog 实现可复用 INT8 GEMM/Conv kernel，覆盖 tiny CNN、projection 和 action MLP 的矩阵乘。支持 AXI4-MM/AXI4-Stream 规定的数据路径和 AXI4-Lite 控制接口。

## 交付物

- kernel source；
- C testbench；
- HLS synthesis/co-simulation report；
- IP package；
- resource/latency baseline。

## 详细验收

- C simulation 与 T002 INT8 reference 对齐；
- HLS co-simulation 通过；
- II、latency、DSP、BRAM、URAM、LUT、FF 已记录；
- 没有动态内存、不可综合代码或 CPU fallback；
- thermo-nuclear review 检查 tile/parallelism abstraction 是否导致复杂分支或重复 kernel；
- PR 包含报告和可复现构建命令。
