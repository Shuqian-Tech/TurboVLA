# TurboVLA-Lite MVP 接口契约

机器可读的唯一来源是 [`hardware/contracts/turbovla_lite_contract.json`](../../hardware/contracts/turbovla_lite_contract.json)。本文件解释接口边界和硬件约束；如果两者不一致，以 JSON contract 为准，并必须先修订 contract 版本。

## 固定输入

```text
image          uint8  [1, 1, 3, 128, 128]  N V C H W, RGB
state          int16  [1, 8]
instruction_id uint16 [1], 有效范围 0..255，65535 保留为 invalid
```

图像预处理在 PL 完成。PS 不得把已处理的视觉特征作为替代输入提交给推理 kernel，否则测试应失败。state 使用 `libero_state_v1` 归一化规则；v0.3 从 `model.bin` header offset 80 读取 finite、strictly-positive little-endian FP32 `state_input_scale`，该值由 checkpoint 校准结果冻结，不得在 PL 中硬编码。

## 固定中间输出

```text
language_embedding int8 [1, 128]
visual_tokens      int8 [1, 32, 128]
fusion output      int8 [1, 32, 128]
```

`language_embedding` 由 PL 中的 instruction embedding table 查表得到。instruction table 的生成来源可以是离线 BERT teacher，但 runtime 不执行 BERT，也不接受动态文本字符串。

## 固定动作输出

```text
action_model int8    [1, 12, 7]
action       float32 [1, 12, 7]
```

PL 负责 action 的反量化，PS 只做机器人相关的限幅、急停和通信。action 范围是 `[-1, 1]`，反归一化统计属于 `libero_action_v1` 参数 metadata，不写死在 runtime 分支中。

## Arena 和寄存器规则

Runtime ABI `0.3.0` 使用一个 64-byte 对齐、200320-byte 的连续 arena。header、image、state、model 和 action 都位于固定的 64-byte 对齐 offset；HLS top 通过一个 AXI4-MM master 访问它们，不再使用未连接的 AXI DMA。

- 模型在初始化时写入 arena 并 flush 一次；每帧启动前分别 flush header、image 和 state；
- 完成 interrupt 后 invalidate header 和 action，再读取 error、hardware version、completed sequence 和 84 个 action；
- `0x10` 是 HLS `ap_return`；arena 的 64-bit DDR 物理地址写入 `0x18/0x1c` 的 low/high AXI-Lite register；
- 控制采用 Vitis HLS 标准 `ap_ctrl_hs`，包括 start/done/idle/ready 和 GIE/IER/ISR；
- `done` 只表示 action 和 completion header 已写完，不表示机器人已执行动作；
- `ap_return` 或 arena header 的 `error_code` 非零时，runtime 不返回 action；
- `contract_version` 使用 `major_minor_patch_8_8_16` 编码；当前 `0.3.0` 对应 `0x00030000`；
- request version、model version 或 PL 写回的 hardware version 不匹配时，runtime 必须拒绝该结果。

v0.3 保持 v0.2 的 arena、tensor offsets、model 大小和计算图不变，只使用 model header 的保留字节 `80..83` 传递 `state_input_scale`。v0.2 model/request 必须被 v0.3 runtime 和 PL 拒绝。

## 不变量

1. batch 永远为 1；
2. view 永远为 1，软件 API 仍保留 view 维度；
3. action horizon 永远为 12，action dim 永远为 7；
4. 所有硬件 kernel 的累加器至少为 INT32；
5. 不允许隐式 reshape、隐式 dtype 转换或 CPU inference fallback；
6. 任何 shape、layout、scale、register 或 error code 变更都必须提升 contract 版本并单独走任务验收；v0.3 state scale 变更由 T015 验收。

## 校验

运行：

```bash
python tools/validate_mvp_contract.py
```

该命令只检查 contract 内部一致性，不需要 KR260 或 Vivado；硬件连通性和 post-route timing 属于后续任务。
