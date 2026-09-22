# T015：升级 state INT8 scale 合同

- 状态：`in_progress`
- Sprint：Sprint 1（跨 Sprint 2/3 验证）
- 分支：`task/T015-state-scale-contract`
- PR：[Shuqian-Tech/TurboVLA#4](https://github.com/Shuqian-Tech/TurboVLA/pull/4)（Draft）
- 依赖：T001、T013、T014
- 后续任务：T004 正式参数包、T014 最终验收
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务动机

T014 正式 QAT checkpoint 校准得到 `state_input_scale=0.025436761811023622`，而
v0.2 PL kernel 将该 scale 硬编码为 `1/127`。验证集归一化 state 最大绝对值为
`3.23046875`；v0.2 只能表示约 `[-1.008, 1.0]`，会把不同的大幅 state 截成相同
INT8 值。保持 v0.2 固定 scale 的 matched QAT 只有 `20/30`，低于原 QAT 的
`23/30`，因此不通过修改模型来吸收错误 ABI。

## 范围

- 将 runtime/model ABI 从 `0.2.0` 升级为 `0.3.0`（encoded `0x00030000`）；
- 在现有 128-byte model header 的 offset 80 写入 little-endian FP32
  `state_input_scale`；
- HLS 从 model header 读取该值，禁止继续使用硬编码 scale；
- 保持 model 总大小、tensor offsets、网络结构、权重和 action shape 不变；
- 保持选定 QAT checkpoint 不变，SHA256 为
  `7209a40065aa72628bd1a2b3b92d92a205ac97a4bb1a4577c1e4eda3d5d5dc1a`；
- 重新执行 C-sim、RTL co-sim、Vivado synthesis/implementation/post-route、
  bitstream/XSA 和 KR260 非破坏性 action parity。

## 交付物

- v0.3 machine-readable contract 和文档；
- v0.3 HLS/runtime ABI 实现与一致性测试；
- 使用原 QAT checkpoint 生成的正式 `model.bin`；
- 软件 exact INT8、HLS/RTL 与 KR260 action parity 报告；
- Vivado timing/resource/power/CDC、bitstream 和 XSA 证据。

## 验收标准

- v0.2 request/model 必须被 v0.3 runtime/PL fail-fast 拒绝；
- state scale header offset、dtype、endianness 和范围由 contract 唯一定义；
- 19 个 tensor 的 shape/offset 与 v0.2 完全一致，`model.bin` 仍为 150656 bytes；
- 原 QAT checkpoint 不重训、不改权重；
- Python exact INT8 与 HLS/RTL action 达到既有 parity 阈值；
- Vivado post-route timing、资源、功耗和 CDC gate 通过并生成 bitstream/XSA；
- KR260 结果单独记录，不用软件报告冒充上板证据；
- thermo-nuclear review 无未处置 blocking finding。

## 当前执行记录

- 开始时间：2026-09-21
- 当前分支：`task/T015-state-scale-contract`
- PR：[Shuqian-Tech/TurboVLA#4](https://github.com/Shuqian-Tech/TurboVLA/pull/4)（Draft）
- hardware bring-up：`not_run`
- 触发证据：T014 state-scale audit；固定 v0.2 scale QAT 为 `20/30`
- v0.3 contract、runtime、HLS 和正式 checkpoint exporter 已实现；RTL/Vivado/板端 gate 待精确 commit 推送后执行

## 本地验证记录

- 正式 QAT checkpoint SHA256：`7209a40065aa72628bd1a2b3b92d92a205ac97a4bb1a4577c1e4eda3d5d5dc1a`（未重训、未修改）
- 正式 v0.3 `model.bin`：150656 bytes，19 tensors，SHA256 `6df32b27eb8a730027c6f37af8c8bd33058700293941a44eae6ade0697fa3886`
- 正式 pack manifest SHA256：`e030312aa841cced64a2a0fc363357a7979af1fe95e16611f2444246bb97b0e7`
- header offset 80 的 little-endian FP32 scale：`0.02543676272034645`（checkpoint double 经 ABI FP32 编码）
- 正式 replay vector 使用 validation index 10281，归一化 state 最大绝对值 `3.23046875`
- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：33 tests 通过
- changed-file `ruff check`：通过
- `python3 tools/run_runtime_csim.py`：通过；v0.2 model 与非法 scale 均 fail-fast
- `python3 tools/run_e2e_csim.py --fixture-dir tests/data/lite_parameter_pack_qat`：通过；action max/mean absolute error `5.96046e-08 / 1.58657e-08`，v0.2 request/model 与非法 scale gate 通过
- 100-sample exact INT8 export round-trip：max/mean absolute error `0.0 / 0.0`；报告 `tests/data/lite_parameter_pack_qat/parity_report.json`
- 尚未运行：Vitis HLS RTL co-sim、Vivado synthesis/implementation/post-route、bitstream/XSA、KR260 action parity
