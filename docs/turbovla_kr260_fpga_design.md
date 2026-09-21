# TurboVLA 在 KR260/K26 上的纯 FPGA 设计方案

## 文档信息

- 记录时间：2026-09-19 00:05:31 EDT (UTC-04:00)
- 目标平台：AMD Kria KR260 Robotics Starter Kit / K26 SOM
- 推理边界：不使用 Vitis AI/DPU；神经网络推理全部在 FPGA PL 中执行
- PS 角色：Linux/ROS2、相机与机器人 I/O、DMA、控制寄存器和任务调度
- 第一目标：TurboVLA LIBERO 配置，2 路视角、7 维动作、12 步 action chunk

## 1. 总体判断

KR260 的 K26 适合实现自定义的 Transformer/NPU 数据流加速器，但不适合把原始 PyTorch 模型直接转换成硬件。K26 约有 256K logic cells、1,248 个 DSP、144 个 BRAM、64 个 UltraRAM 和 4GB DDR4。片上 BRAM 与 UltraRAM 合计约 3MB，因此模型权重必须放在 DDR 中，由 PL 通过 AXI HP/HPC 端口分层搬运。

TurboVLA 的主要负载是 DINOv3 ViT、BERT、多头注意力、FFN、LayerNorm 和 action decoder。设计重点应是可复用的 tiled GEMM、attention、LayerNorm、softmax 和非线性计算单元，而不是针对某一层复制专用硬件。

原始约 0.2B 参数模型可以作为参考模型，但不应一开始就以“完整原模型在 KR260 上 32Hz”为验收目标。第一版应先完成固定 shape、逐层数值对齐和闭环运行，再通过蒸馏、量化和结构裁剪提升吞吐。

## 2. 系统边界

```text
PS: Linux + ROS2 + 相机/机器人驱动
    DMA descriptor / AXI-Lite 控制 / 状态与错误管理
             |
             v
PL: 图像预处理
    -> DINOv3 或 FPGA student vision encoder
    -> vision projection
    -> BERT encoder
    -> vision-language interaction
    -> state projection + ACT action decoder
    -> 量化、反量化和动作输出
             |
             v
PS: 动作安全检查、关节限幅、急停和机器人命令
```

“推理全在 FPGA”指所有神经网络层和推理数据通路在 PL 中执行。文本 tokenizer 可以先保留在 PS；如果系统要求连 tokenizer 也在 FPGA，需要额外实现 WordPiece 词表查找、截断、padding 和 mask 生成，但这不是第一阶段的性能瓶颈。

## 3. TurboVLA 第一目标的固定形状

| 项目 | 第一版建议 |
|---|---:|
| 视角数 | 2 |
| 图像尺寸 | 224 或 256，需与训练配置一致 |
| DINOv3 patch | ViT-B/16，256x256 时每视角约 256 个 patch |
| 视觉 token | 约 512 |
| 文本长度 | 固定 32 或 64，不使用动态 256 |
| interaction hidden dim | 256 |
| interaction layers | 先 3 层，再尝试恢复 6 层 |
| state tokens | 2 |
| action horizon | 12 |
| action dim | 7 |
| GEMM 精度 | INT8 权重/激活，INT32 累加 |
| LayerNorm/softmax | 第一版允许 INT16/FP16 混合，之后再定点化 |

RoboTwin 的 3 路视角、14 维动作和 50 步 horizon 应放到第二阶段，避免同时引入更大的 token 数和 action decoder 压力。

## 4. PL 硬件模块

### 4.1 共享 tiled GEMM 阵列

矩阵乘覆盖以下模块：

- DINOv3 和 BERT 的 Q/K/V projection、FFN；
- vision-language cross attention；
- action decoder；
- vision projection、state projection 和 action MLP。

建议使用参数化的 16x16 或 32x32 systolic/tiled 阵列，具体并行度以 Vivado 综合后的 DSP、时序和 DDR 带宽为准。不要为每个 Transformer 层复制一套矩阵阵列。

数据路径：

```text
DDR -> activation tile / weight tile -> GEMM
                                  -> INT32 accumulator
                                  -> scale + bias
                                  -> activation / residual
                                  -> output tile
```

### 4.2 Attention engine

不要把完整 attention matrix 写回 DDR。按 query row 或 token block 流式执行：

```text
Q block -> QK^T -> online softmax -> probability * V -> output projection
```

需要的硬件单元包括：Q/K/V projection、block GEMM、mask、online softmax、output projection 和 residual。softmax 第一版可使用 LUT、分段线性近似、最大值减法和定点 reciprocal；不建议直接综合通用浮点 `exp`。

### 4.3 LayerNorm、GELU 和非线性

- LayerNorm：通道求和、平方和、rsqrt LUT/迭代、scale/bias；
- GELU：分段线性或 LUT；
- tanh：action 输出端使用 LUT 或定点近似；
- residual/add：独立流水单元，避免回到 PS。

### 4.4 片上缓存与 DMA

- DDR：checkpoint 权重和较大的 activation buffer；
- URAM：当前层权重 tile、视觉/text token buffer；
- BRAM：Q/K/V tile、softmax 临时结果、LayerNorm 中间量；
- 双缓冲：一块 buffer 计算时，另一块 buffer 通过 DMA 搬运；
- 权重尽量按 layer 加载并在多个 token/view 上复用。

INT8 模型权重约为 200MB，INT16 约为 400MB。若每次推理都完整读取权重，DDR 流量会成为主要瓶颈，因此必须使用权重复用和层内 tile 缓存。

## 5. 推理数据流

1. PL 对两路图像执行 resize、normalize 和布局转换。
2. DINOv3 输出视觉 patch tokens，并经过 vision projection 降到 256 维。
3. BERT 对固定长度 token sequence 编码；文本变化时重新执行，连续控制帧可复用结果。
4. 6 层或裁剪后的 3 层 vision-language interaction 执行双向 cross attention、text self attention、FFN 和 LayerNorm。
5. state projection 生成两个 state tokens。
6. ACT decoder 使用 12 个 action queries 输出 12x7 action chunk。
7. PL 完成反量化；PS 只做动作安全检查、归一化还原和机器人通信。

## 6. 量化策略

建议采用渐进式方案：

1. FP32 软件参考模型，保存逐层输出。
2. INT8 GEMM + FP16 LayerNorm/softmax，验证结构和 DMA。
3. INT8 权重、INT8 激活、INT32 累加，使用代表性观测集校准。
4. 对 DINOv3、BERT 和 interaction 做量化感知训练（QAT）。
5. 最后再将 softmax、LayerNorm、GELU 和 tanh 改为全定点。

校准集应包含不同相机视角、不同语言指令、不同机器人状态和动作边界。必须逐层比较最大绝对误差、均方误差和最终 action MAE，不能只比较任务成功率。

## 7. 开发阶段

### 阶段 1：算子和存储验证

- 实现 INT8 GEMM；
- 实现 LayerNorm、GELU、softmax；
- 验证 AXI DMA、DDR、BRAM/URAM 双缓冲；
- 使用随机张量完成 Python/C++/RTL 对齐。

### 阶段 2：单层 Transformer 对齐

实现一层完整路径：

```text
QKV -> attention -> output projection -> residual -> LayerNorm
     -> FFN -> residual -> LayerNorm
```

先完成 bit-accurate 或明确误差界限的对齐，再扩展层数。

### 阶段 3：interaction + action head

先将视觉 token 和 text token 作为输入，完成完整 action chunk 输出。这个阶段可以验证控制闭环和动作数值，不必等待 DINOv3 完成。

### 阶段 4：视觉 backbone

先尝试原始 DINOv3 ViT-B/16；如果资源或带宽不可接受，则用 DINOv3 teacher 蒸馏出 FPGA-friendly student ViT/CNN，并重新微调 TurboVLA。

## 8. 验收指标

- 功能：LIBERO 单帧输入到 12 步 action chunk 的完整闭环；
- 数值：每个硬件子模块与 FP32 reference 对齐；
- 质量：量化后 LIBERO 成功率下降控制在 2 个百分点以内；
- 性能：记录端到端 p50/p99 latency、PL kernel latency、DDR 带宽和功耗；
- 稳定性：连续运行至少 30 分钟，检查 DMA、DDR 和动作输出是否出现漂移；
- 安全：动作限幅、超时、急停和非法状态必须在机器人执行前生效。

## 9. 代码和工程目录建议

```text
hardware/
  gemm/
  attention/
  layernorm/
  softmax/
  gelu/
  vision_encoder/
  text_encoder/
  action_head/
  vivado_kr260/

runtime/
  turbovla_pl_controller.cpp
  dma_buffer.cpp
  ros2_policy_node.cpp

tools/
  export_fixed_shape.py
  calibrate_int8.py
  compare_fpga_reference.py
```

当前仓库没有 ONNX、HLS、Vitis、xclbin、xmodel 或 KR260 平台工程，因此下一步应先建立固定 shape 的软件 reference 和一个可综合的 GEMM/attention 原型。

## 10. 关键风险

1. 原始 0.2B 模型的 DDR 权重流量可能限制吞吐；
2. DINOv3 和 BERT 的 LayerNorm、softmax、GELU 对低比特量化敏感；
3. 动态文本长度会破坏硬件流水线，应固定为 32/64；
4. 全部使用 FP32 会严重增加 DSP、存储和带宽压力；
5. 直接以 32Hz 作为 KR260 第一版指标风险很高，应先完成正确性和闭环，再进行模型蒸馏与并行度优化。

## 11. Vivado 实现入口

FPGA kernel 的编写规范、Vivado block design、HLS/RTL 选择、综合与布局布线流程记录在 [Vivado 实现与编译流程](vivado_flow.md)。该流程明确要求使用可综合的 HLS C++ 或 RTL，并以 post-route timing、资源报告和逐层数值对齐作为硬件版本的验收依据。

## 12. 第一版 MVP

第一版采用 [TurboVLA-KR260 纯 FPGA MVP](mvp.md)：1 路视角、128x128、tiny CNN student、instruction embedding table、2 层融合和 12x7 action MLP。它保留视觉+语言到动作的核心路径，但不直接硬化原始 DINOv3/BERT checkpoint；当前迭代见 [Sprint 1](sprint/sprint-1-model-contract.md)，逐任务索引见 [Tasks README](tasks/README.md)。
