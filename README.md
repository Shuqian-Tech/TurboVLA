# TurboVLA-Lite：AMD KR260 上的纯 FPGA VLA 推理实验

本仓库将 [TurboVLA](https://github.com/H-EmbodVis/TurboVLA) 压缩为面向 AMD Kria KR260/K26 的 **TurboVLA-Lite**，并完成从模型蒸馏、INT8 参数导出、HLS/RTL 验证、Vivado 实现到真实开发板运行的完整流程。神经网络推理全部在 FPGA PL 中执行；PS 只负责缓冲区、缓存同步、AXI-Lite 控制、轮询和结果校验，不使用 DPU、Vitis AI 或 CPU 推理回退。

> 当前结果是单视角、固定指令集合的 FPGA MVP，不代表原始 TurboVLA 模型被逐层原样移植，也不包含真实机器人闭环结果。

## 实验结果概览

| 项目 | 结果 |
| --- | ---: |
| 目标平台 | AMD Kria KR260 / K26，`xck26-sfvc784-2LV-c` |
| PL 时钟 | 目标 `200 MHz`，板端实测 `199.998 MHz` |
| HLS 最大延迟估计 | `3,817,800 cycles`，即 `19.089 ms` @ 200 MHz |
| Vivado post-route 时序 | WNS `+0.013 ns`，TNS `0` |
| KR260 100 样本端到端延迟 | mean `77.449 ms`，p95 `78.440 ms` |
| KR260 100 样本吞吐 | `12.912 inference/s` |
| FPGA 与 exact-INT8 最大误差 | `1.78814e-07` |
| 100 样本板端通过率 | `100/100` |
| 30 分钟稳定性 | `17,019` 次完整推理及 84 值 parity 检查通过 |
| Vivado 估算芯片功耗 | `3.259 W` |
| 板端 100 样本窗口功耗 | mean `3.731 W`，范围 `3.64-4.09 W` |
| 板端 PL 温度 | mean `26.878 C`，范围 `25.024-28.490 C` |

完整 T015 证据见 [HLS、Vivado 与 KR260 实验记录](hardware/vivado_kr260/reports/t015/README.md)。

## TurboVLA-Lite 模型

| 模块 | FPGA MVP 配置 |
| --- | --- |
| 图像输入 | 单视角 `128x128 RGB` |
| 视觉编码 | FPGA-friendly tiny CNN student |
| 语言输入 | 固定 instruction ID + 预计算 embedding table |
| 机器人状态 | 固定 8 维 state |
| 多模态融合 | 两层轻量 fusion / gated fusion |
| 动作输出 | `12 x 7` 连续动作 chunk，共 84 个值 |
| 数值格式 | INT8 权重/激活，INT32 累加，输出反量化 |

数据路径如下。只有控制和数据搬运留在 PS，视觉、语言条件、融合和动作预测都位于 PL：

```text
128x128 RGB ---------> tiny CNN -----------+
                                               |
instruction ID ------> embedding table --------+--> 2-layer fusion
                                               |          |
8-D state -----------> state projection -------+          v
                                                     action MLP
                                                          |
                                                          v
                                                   12x7 actions

PS: XRT buffer / cache sync / AXI-Lite / safety checks
PL: preprocess / CNN / language lookup / fusion / action head
```

## 实现与验证流程

实验严格按以下顺序推进。每一层先与上一层的参考结果对齐，再进入下一层，避免用位流结果掩盖软件或 RTL 数值错误。

```text
TurboVLA teacher
  -> TurboVLA-Lite student 蒸馏
  -> PTQ / QAT 与固定 shape 参数导出
  -> Python exact-INT8 reference
  -> HLS C simulation
  -> HLS synthesis + IP export
  -> 独立 XSIM 进程的 RTL co-simulation
  -> Vivado block design
  -> synthesis
  -> implementation / place / route
  -> post-route timing / resource / power / CDC
  -> bitstream + XSA + KR260 package
  -> KR260 runtime parity
  -> 100 样本 sweep
  -> 30 分钟稳定性验证
```

### 按流程顺序记录的耗时

以下软件构建数据来自 AMD Vitis/Vivado 2025.1、高内存构建机上的 T015 日志，源提交为 `2b88e7f`。板端数据来自 `amd-edf@192.168.68.120`。表中的阶段存在父子包含关系，因此不能把所有行直接相加。

| 顺序 | 阶段 | 实际墙钟时间 | 结果与口径 |
| ---: | --- | ---: | --- |
| 1 | 模型蒸馏与 QAT | 未单独记录 | 训练日志未保存统一端到端计时，不做推算 |
| 2 | HLS C simulation | `4 s` | C testbench 通过 |
| 3 | HLS synthesis | `41 s` | 估算周期 `3.798 ns`，最大延迟 `3,817,800 cycles` |
| 4 | HLS IP export | `23 s` | 生成 Vivado IP catalog archive |
| 5 | RTL case 0：完整推理 parity | XSIM `1 h 45 m 10 s` | 单独 XSIM 进程；整次 Vitis 调用为 `1 h 48 m 30 s`，peak RSS `111,802,256 KB` |
| 6 | RTL case 1：非法 instruction ID | XSIM `5 s` | fail-fast gate 通过 |
| 7 | RTL case 2：拒绝 v0.2 request | XSIM `5 s` | fail-fast gate 通过 |
| 8 | RTL case 3：拒绝 v0.2 model | XSIM `5 s` | fail-fast gate 通过 |
| 9 | RTL case 4：拒绝非正 state scale | XSIM `5 s` | fail-fast gate 通过 |
| 10 | RTL case 5：拒绝非有限 state scale | XSIM `5 s` | fail-fast gate 通过 |
| 11 | RTL cases 1-5 runner 总计 | `9 m 51 s` | 每个 case 使用独立 XSIM；总时间包含各 case 的生成、编译和 elaboration |
| 12 | Vivado block design output products | `30 s` | KR260 PS、SmartConnect、HLS IP 与中断连接 |
| 13 | Vivado synthesis run | `13 m 53 s` | 包含并行 OOC/IP runs；顶层 `synth_design` 本身为 `52 s` |
| 14 | Logic optimization | `30 s` | `opt_design -directive Explore` |
| 15 | Placement | `5 m 42 s` | `place_design -directive Explore` |
| 16 | Routing | `4 m 24 s` | `route_design -directive Explore -tns_cleanup` |
| 17 | Implementation run 总计 | `14 m 45 s` | 包含 opt/place/route、报告、checkpoint 和 run 内 bitstream |
| 18 | 最终 bitstream 写出 | `32 s` | `write_bitstream` 成功 |
| 19 | XSA 写出 | `9 s` | `write_hw_platform -include_bit` 成功 |
| 20 | 完整 Vivado batch | `31 m 34 s` | 从 `02:31:36` 到 `03:03:10`，包含步骤 12-19 |
| 21 | KR260 单次完整 PS/PL 推理 | mean `77.449 ms` | 100 个不同 validation 样本；含 cache、MMIO、轮询与输出 invalidation |
| 22 | KR260 100 样本 sweep | `100/100` | 单板共享执行路径串行运行；每个样本只运行一次 |
| 23 | KR260 稳定性运行 | `30 min` | `17,019` 次推理，无 timeout、PL error、NaN、parity failure 或 reset |

RTL cases 1-5 的 `5 s` 是日志中每个 XSIM session 的起止时间；`9 m 51 s` 才是包含 RTL 重新生成、编译和 elaboration 的完整 runner 时间。case 0 的 `19.089 ms` 是综合报告按时钟换算的理想 PL kernel 延迟，不是 `1 h 45 m 10 s` 的 RTL 仿真墙钟时间，也不是 `77.449 ms` 的真实板端端到端延迟。

原始日志：

- [case 0 HLS/RTL log](hardware/vivado_kr260/reports/t015/turbovla-t015-2b88e7f-case0-hls.log)
- [cases 1-5 HLS/RTL log](hardware/vivado_kr260/reports/t015/turbovla-t015-2b88e7f-cases1-5-hls.log)
- [Vivado batch log](hardware/vivado_kr260/reports/t015/turbovla-t015-2b88e7f-vivado.log)

## 模型与量化结果

固定的 100 个 LIBERO episodes 用于比较 student、量化模型和 teacher。初版 validation-calibrated QAT 与后续 train-only calibration 结果分开报告，避免 calibration/evaluation 数据使用方式造成误导。

| 模型 | 成功次数 | 成功率 | 说明 |
| --- | ---: | ---: | --- |
| TurboVLA-Lite distilled FP32 | `75/100` | `75%` | student baseline |
| TurboVLA-Lite PTQ fake INT8 | `77/100` | `77%` | post-training quantization |
| TurboVLA-Lite QAT fake INT8 | `78/100` | `78%` | validation-calibrated 初版 |
| TurboVLA-Lite train-only QAT | `79/100` | `79%` | calibration 仅使用 51,109 个 train samples |
| TurboVLA teacher BF16 | `95/100` | `95%` | teacher/reference，不是 FPGA runtime |

train-only QAT 的 validation action MAE 为 `0.129080477`，gripper sign accuracy 为 `92.3635%`。这些是 LIBERO 仿真/离线模型指标；板端 `100/100` 表示 100 次 FPGA 调用和 exact-INT8 parity 全部通过，并不表示机器人任务成功率为 100%。详细评估见 [GPU TinyCNN pilot](docs/evaluation/t014_gpu_tinycnn_pilot.md)。

## RTL 与数值一致性

T015 将昂贵的完整推理与五个 fail-fast contract case 分到六个独立 XSIM 进程，避免 XSIM 内存随 transaction 累积：

| Case | 验证内容 | 结果 |
| ---: | --- | --- |
| 0 | 完整 84 值 action parity | PASS，max `1.19209e-07`，mean `1.98128e-08` |
| 1 | 非法 instruction ID | PASS |
| 2 | v0.2 request version rejection | PASS |
| 3 | v0.2 model version rejection | PASS |
| 4 | 非正 state scale rejection | PASS |
| 5 | 非有限 state scale rejection | PASS |

case 0 的 XSIM peak RSS 为 `111,802,256 KB`，因此完整推理 co-simulation 需要高内存主机，不能把多个完整 case 合并到同一模拟器进程。

## Vivado post-route 结果

| 指标 | 结果 |
| --- | ---: |
| 目标器件 | `xck26-sfvc784-2LV-c` |
| 目标频率 | `200 MHz` |
| Setup WNS / TNS | `+0.013166 ns` / `0 ns` |
| Hold WHS / THS | `+0.010 ns` / `0 ns` |
| LUT | `29.23%` |
| FF | `16.55%` |
| DSP | `13.46%` |
| BRAM | `5.21%` |
| URAM | `0%` |
| 估算总片上功耗 | `3.259 W` |
| 产物 | bitstream 与 XSA 均成功生成 |

报告入口：[timing](hardware/vivado_kr260/reports/t015/timing_summary.rpt)、[utilization](hardware/vivado_kr260/reports/t015/utilization.rpt)、[power](hardware/vivado_kr260/reports/t015/power.rpt)、[CDC](hardware/vivado_kr260/reports/t015/cdc.rpt)。

## KR260 实测

### 100 样本 validation sweep

100 个不同样本从固定 validation split 均匀选取，并通过同一个 UIO/XRT 执行路径串行运行：

| 指标 | validation-calibrated QAT | train-only QAT |
| --- | ---: | ---: |
| 成功调用 | `100/100` | `100/100` |
| mean latency | `77.449 ms` | `76.076 ms` |
| p95 latency | `78.440 ms` | `76.110 ms` |
| throughput | `12.912 Hz` | `13.145 Hz` |
| FPGA/exact-INT8 worst max error | `1.78814e-07` | `1.19209e-07` |

validation-calibrated sweep 的原始聚合数据见 [validation100_board_sweep.json](hardware/vivado_kr260/reports/t015/validation100_board_sweep.json)。

### HLS 估算与真实板端延迟

HLS 报告的最大 latency 为 `3,817,800 cycles`，在板端 `199.998 MHz` 时钟下对应 `19.089 ms`，理论约 `52.386 Hz`。真实完整调用约 `77 ms`，约为该理想核估算的 `4.04x`；差距包含 PS cache maintenance、AXI-Lite 提交、MMIO polling、内存访问和输出 invalidation，不能解释为纯 PL 计算时间。

### RTX 3070 离线对照

| 路径 | Mean | p95 | 吞吐 |
| --- | ---: | ---: | ---: |
| RTX 3070 train-only QAT E2E | `3.420 ms` | `4.705 ms` | `292.43 samples/s` |
| KR260 train-only exact-INT8 PS/PL | `76.076 ms` | `76.110 ms` | `13.145 Hz` |

GPU 数字使用预加载输入，包括 CPU tensor preparation、H2D、QAT forward、D2H 和 CUDA synchronization；FPGA 数字包括板端 PS/PL 控制开销。该表是系统级离线对照，不表示 GPU 参与 FPGA 部署路径。

## 复现实验

需要 AMD Vitis/Vivado 2025.1。高内存 RTL co-simulation 和 Vivado 构建应在独立 worktree 中进行。

```bash
# 软件 contract 与 host runtime
python3 tools/validate_mvp_contract.py
python3 tools/validate_kr260_block_manifest.py
python3 tools/run_runtime_csim.py

# case 0：完整推理，必须独立运行
TURBOVLA_HLS_SYNTH=1 \
TURBOVLA_E2E_FIXTURE_DIR=tests/data/lite_parameter_pack_qat \
TURBOVLA_E2E_COSIM_CASES=0 \
tools/run_vitis_hls.sh hardware/hls/e2e/vitis_hls.tcl

# cases 1-5：每个 case 仍由 Tcl runner 启动独立 XSIM
TURBOVLA_HLS_SYNTH=1 \
TURBOVLA_E2E_FIXTURE_DIR=tests/data/lite_parameter_pack_qat \
TURBOVLA_E2E_COSIM_CASES="1 2 3 4 5" \
tools/run_vitis_hls.sh hardware/hls/e2e/vitis_hls.tcl

# KR260 Vivado synthesis、implementation、reports、bitstream 与 XSA
vivado -mode batch -source hardware/vivado_kr260/build.tcl
```

开发细节和报告要求见 [Vivado flow](docs/vivado_flow.md)。仓库中的板端地址是实验环境信息；加载或重配置 FPGA 前仍应确认目标板、bitstream、device tree overlay 和当前运行状态。

## 证据索引

- [T015 完整 HLS/Vivado/板端记录](hardware/vivado_kr260/reports/t015/README.md)
- [T013 HLS 与 Vivado 报告](hardware/vivado_kr260/reports/t013/README.md)
- [T013 30 分钟板端稳定性](hardware/vivado_kr260/reports/t013_board_bringup.md)
- [T009 五组 runtime fixture bring-up](hardware/vivado_kr260/reports/t009_runtime_bringup.md)
- [TurboVLA-Lite MVP 边界](docs/mvp.md)
- [当前开发状态](docs/development_status.md)

## 上游项目与许可证

本项目基于论文 **TurboVLA: Real-Time Vision-Language-Action Model at 32 Hz on an RTX 4090 with <1 GB VRAM** 的官方实现扩展：

- 论文：[arXiv:2607.27205](https://arxiv.org/abs/2607.27205)
- 上游代码：[H-EmbodVis/TurboVLA](https://github.com/H-EmbodVis/TurboVLA)
- 上游模型：[Hugging Face](https://huggingface.co/H-EmbodVis/TurboVLA)
- 许可证：[Apache 2.0](LICENSE)

原始 DINOv3/BERT checkpoint 在本 FPGA MVP 中仅作为 teacher/reference，不是 KR260 运行时依赖。
