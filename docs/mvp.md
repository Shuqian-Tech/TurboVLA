# TurboVLA-KR260 纯 FPGA MVP

## 文档信息

- 记录时间：2026-09-19 00:23:30 EDT (UTC-04:00)
- 目标：用最高可行性方案完成 KR260 上的纯 FPGA VLA 闭环
- FPGA 边界：神经网络推理全部在 PL，禁止 DPU 和 CPU fallback
- PS 边界：相机/机器人 I/O、ROS2、DMA、AXI-Lite 控制、动作安全保护
- 第一场景：LIBERO 风格单臂任务

## 1. MVP 的核心决策

第一版不直接把原始 TurboVLA 的 DINOv3 ViT-B、BERT base、6 层 interaction 和 ACT decoder 原样搬进 FPGA。原始模型可以继续作为 teacher/reference，但直接硬化会同时暴露模型规模、动态文本、低比特量化、DDR 带宽和 Vivado 时序五个风险。

MVP 采用一个重新训练/蒸馏的 **TurboVLA-Lite**：保留“视觉 + 语言 -> 连续动作 chunk”的任务定义，改变 backbone 和固定 shape，使它适合 KR260 的自定义 HLS/RTL 数据流。MVP 的目标不是宣称与原始 checkpoint bit-exact，而是先完成真实相机输入到 FPGA action 输出的稳定闭环。

## 2. MVP 模型定义

| 模块 | MVP 配置 | 选择理由 |
|---|---|---|
| 视角 | 1 路起步，接口预留 2 路 | 先减少 DMA 和视觉计算风险 |
| 输入 | 128x128 RGB | 固定 shape，降低带宽和片上 buffer 压力 |
| 视觉 encoder | FPGA-friendly tiny CNN/浅层 CNN student | 卷积、ReLU、池化容易做 line buffer 和 tiled MAC |
| 视觉 token | 16 或 32 个 | 控制 attention matrix 和激活存储 |
| 文本输入 | 固定 instruction ID，查表得到 1 个 language token | 避免在线 BERT 和动态 WordPiece |
| 文本 embedding | 由 BERT teacher 离线生成，MVP 权重固化到 DDR/BRAM | 保留语言条件，同时让 runtime 全在 PL |
| hidden dim | 128 | 降低 DSP、BRAM 和 DDR 流量 |
| vision-language fusion | 2 层 cross-attention 或 gated fusion | 保留 V+L 交互，规模可控 |
| state | 8 维固定 state | 与 LIBERO 默认 action/state 接口对齐 |
| action head | MLP，输出 12x7 | 第一版不实现完整 Transformer decoder |
| 权重/激活 | INT8 / INT8，INT32 累加 | 适合 DSP 和 DDR 带宽 |
| 非线性 | ReLU 或 LUT；LayerNorm 可先用 INT16 | 先减少浮点硬件风险 |

MVP 可以先使用单路相机，但软件和硬件接口必须使用 `[B,V,C,H,W]` 形式，第二阶段只增加 `V=2` 的并行/时分复用，不改变 runtime API。

## 3. 为什么不在 MVP 做在线 BERT

LIBERO 的语言指令集合在评测期间通常是有限的。MVP 将每条 instruction 映射为一个 ID，预先用原始 BERT 生成 language embedding，并把 embedding 表作为模型参数的一部分加载到 FPGA。运行时的文本条件选择、视觉编码、融合和动作预测仍全部在 PL。

这不是最终产品形态，但它把最大的软件/硬件不确定性从 MVP 中移除。在线 tokenizer+BERT 应作为后续扩展；如果最终必须支持任意自然语言，再单独增加一个固定长度、缩小 hidden size 的 FPGA text encoder。

## 4. PL 数据流

```text
AXI DMA: image + state + instruction_id
        |
        v
image preprocess
        |
        v
tiny CNN student -> visual tokens
        |
        +--> language embedding table -> language token
        |
        v
2-layer fusion / gated cross attention
        |
        v
state projection + action MLP
        |
        v
12x7 INT8 action chunk
        |
        v
dequantize / clamp -> AXI DMA -> PS safety layer
```

第一版只需要以下可复用 kernel：

1. `conv_gemm` 或统一的 `matmul`；
2. `pool_relu`；
3. `fusion_attention` 或 `gated_fusion`；
4. `layernorm_or_scale`；
5. `action_mlp`；
6. DMA buffer manager 和 AXI-Lite scheduler。

如果 attention 的 softmax 在时序或资源上成为阻塞，MVP 优先使用 gated fusion；等 GEMM、DMA 和动作闭环稳定后，再替换成 cross-attention。

## 5. MVP 的 Vivado 实现

```text
Zynq UltraScale+ PS
  ├── DDR
  ├── AXI SmartConnect
  ├── AXI DMA
  ├── AXI-Lite scheduler
  ├── image preprocess IP
  ├── tiny CNN / GEMM IP
  ├── fusion IP
  ├── action MLP IP
  └── interrupt controller
```

代码采用 HLS C++ 或 SystemVerilog，最终由 Vivado 完成综合、布局布线和 bitstream：

```text
PyTorch teacher/student reference
  -> fixed-shape export and calibration
  -> HLS C simulation
  -> HLS synthesis / co-simulation
  -> Vivado IP packaging
  -> Vivado block design
  -> synthesis / implementation / post-route timing
  -> bitstream + XSA
  -> KR260 runtime test
```

MVP 不允许未实现的算子回退到 PS。任何 PL kernel 缺失都应使测试失败，而不是静默调用 CPU。

## 6. 软件训练和蒸馏工作

需要先生成 TurboVLA-Lite checkpoint：

1. 用现有 TurboVLA teacher 在 LIBERO 训练/评测数据上生成视觉特征、language embedding 和 action targets；
2. 训练 tiny CNN + fusion + action MLP student；
3. 加入 INT8 fake quantization；
4. 以 FP32 student 和 teacher action 为联合监督；
5. 导出固定 shape、无 dropout 的 inference graph；
6. 生成 instruction embedding table、量化 scale、bias 和 normalization metadata。

蒸馏完成前不要开始大规模 RTL 优化，否则硬件会绑定在尚未稳定的网络结构上。

## 7. MVP 验收标准

### 功能

- KR260 实机能加载 bitstream；
- PS 能通过 DMA 提交图像、state 和 instruction ID；
- PL 输出完整的 12x7 action chunk；
- 连续运行时没有 CPU inference fallback；
- 能接入一个真实或回放的机器人控制循环。

### 数值

- HLS/RTL 输出与 Python INT8 reference 对齐；
- action 的最大绝对误差和平均绝对误差有固定阈值并自动检查；
- 量化 student 在目标 LIBERO 子集上的成功率下降不超过预先约定的基线范围。

### 硬件

- post-route timing 无 violation；
- 记录 LUT、FF、DSP、BRAM、URAM、DDR 带宽和功耗；
- 连续运行 30 分钟无 DMA 错误、状态漂移或动作 NaN；
- 每次 bitstream 都保存 Vivado report、XSA、硬件版本和 git commit。

## 8. MVP 明确不做的事情

- 不做 RoboTwin 三视角、14 维动作、50 步 horizon；
- 不做原始 DINOv3 ViT-B 的完整 FPGA 化；
- 不做在线 BERT 和任意长度自然语言；
- 不做 32Hz 性能承诺；
- 不做完整 6 层大 hidden-dim Transformer；
- 不做 DPU、Vitis AI 或 CPU fallback。

## 9. MVP 完成后的升级路径

```text
MVP: 1 view + instruction table + tiny CNN + gated fusion
  -> 2 views
  -> cross-attention
  -> 更大的视觉 student
  -> 在线小型 text encoder
  -> 6-layer interaction
  -> 原始 DINOv3/BERT 的分阶段硬化
```

每次升级都必须重新通过软件 reference、定点误差、Vivado post-route timing 和实机闭环四个门槛。
