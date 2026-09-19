# TurboVLA-Lite MVP 接口契约

机器可读的唯一来源是 [`hardware/contracts/turbovla_lite_contract.json`](../../hardware/contracts/turbovla_lite_contract.json)。本文件解释接口边界和硬件约束；如果两者不一致，以 JSON contract 为准，并必须先修订 contract 版本。

## 固定输入

```text
image          uint8  [1, 1, 3, 128, 128]  N V C H W, RGB
state          int16  [1, 8]
instruction_id uint16 [1], 65535 保留为 invalid
```

图像预处理在 PL 完成。PS 不得把已处理的视觉特征作为替代输入提交给推理 kernel，否则测试应失败。state 使用 `libero_state_v1` 归一化规则，具体统计值由参数包任务冻结。

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

## DMA 和寄存器规则

- 所有 DMA buffer 64-byte 对齐；
- PS -> PL buffer 在启动 DMA 前 flush cache；
- PL -> PS action buffer 在完成 interrupt 后 invalidate cache；
- 64-bit DDR 地址拆成 low/high 两个 32-bit register；
- `control.start` 只能在 `status.idle=1` 且上一帧 error 已清除时写入；
- `status.done` 只表示 action buffer 已写完，不表示机器人已执行动作；
- `error_code` 非零时，runtime 必须停止发起新帧，直到写 `error_clear` 并完成 reset/恢复流程；
- `contract_version` 使用 `major_minor_patch_8_8_16` 编码；当前 `0.1.0` 对应 `0x00010000`；
- `contract_version` 不匹配时，PS 必须拒绝启动 bitstream。

## 不变量

1. batch 永远为 1；
2. view 永远为 1，软件 API 仍保留 view 维度；
3. action horizon 永远为 12，action dim 永远为 7；
4. 所有硬件 kernel 的累加器至少为 INT32；
5. 不允许隐式 reshape、隐式 dtype 转换或 CPU inference fallback；
6. 任何 shape、layout、scale、register 或 error code 变更都必须提升 contract 版本并单独走任务验收。

## 校验

运行：

```bash
python tools/validate_mvp_contract.py
```

该命令只检查 contract 内部一致性，不需要 KR260 或 Vivado；硬件连通性和 post-route timing 属于后续任务。
