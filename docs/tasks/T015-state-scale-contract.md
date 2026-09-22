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
- hardware bring-up：`passed`（2026-09-22；正确板端为 `192.168.68.120`，T015 package 已加载，probe、PL action parity 和 12 次 live invocation 通过）
- 触发证据：T014 state-scale audit；固定 v0.2 scale QAT 为 `20/30`
- v0.3 contract、runtime、HLS 和正式 checkpoint exporter 已实现；精确 commit `2b88e7f` 已完成 RTL/Vivado/package gate，板端 gate 仍待板端网络恢复

## 本地验证记录

- 正式 QAT checkpoint SHA256：`7209a40065aa72628bd1a2b3b92d92a205ac97a4bb1a4577c1e4eda3d5d5dc1a`（未重训、未修改）
- 正式 v0.3 `model.bin`：150656 bytes，19 tensors，SHA256 `6df32b27eb8a730027c6f37af8c8bd33058700293941a44eae6ade0697fa3886`
- 正式 pack manifest SHA256：`e030312aa841cced64a2a0fc363357a7979af1fe95e16611f2444246bb97b0e7`
- header offset 80 的 little-endian FP32 scale：`0.02543676272034645`（checkpoint double 经 ABI FP32 编码）
- 正式 replay vector 使用 validation index 10281，归一化 state 最大绝对值 `3.23046875`
- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：35 tests 通过
- changed-file `ruff check`：通过
- `python3 tools/run_runtime_csim.py`：通过；v0.2 model 与非法 scale 均 fail-fast
- `python3 tools/run_e2e_csim.py --fixture-dir tests/data/lite_parameter_pack_qat`：通过；action max/mean absolute error `5.96046e-08 / 1.58657e-08`，v0.2 request/model 与非法 scale gate 通过
- 100-sample exact INT8 export round-trip：max/mean absolute error `0.0 / 0.0`；报告 `tests/data/lite_parameter_pack_qat/parity_report.json`
- Vitis HLS RTL co-sim：case 0 独立通过，cases 1..5 独立通过；case 0 XSIM peak `111802256 KB`，不宣称低于 96 GiB
- Vivado synthesis/implementation/post-route、bitstream/XSA：通过；post-route WNS `+0.01316635683178902 ns`，TNS `0`，WHS `+0.010 ns`，THS `0`
- package：`hardware/vivado_kr260/reports/t015/manifest.json`，control base `0xa0000000`；bit `c0f1e8a7548b7309ff63d63342f2e378c06bbe7c15c62c108be843eea7d80622`，bit.bin `bbb0b7f71029ca11165d2e1401b2b3af82267f0b0818f42381884b5ea9c072ca`，dtbo `a4fe03cd15e4078a3c4d1eeb4b1d6b5a7e89af8e0e2eefbc57e0bf844bad1bc9`
- Hardware Manager 非破坏性枚举：target `127.0.0.1:3121/xilinx_tcf/Xilinx/XFL13WUMT00XA`，devices `xck26_0 arm_dap_1`
- KR260 action parity：通过；`.120` probe passed，full PL inference action `max_abs_error=1.19209e-07`、`mean_abs_error=1.98128e-08`，12/12 live invocations passed；`.119` 缺少 `xrt/xrt_bo.h` 仅影响 host-side compile，不影响板端运行

## 变更与证据索引

- 主要变更文件：`hardware/contracts/turbovla_lite_contract.json`、`hardware/hls/e2e/e2e.cpp`、`hardware/hls/e2e/model_layout.h`、`hardware/hls/e2e/tb_e2e.cpp`、`runtime/include/turbovla_runtime.hpp`、`runtime/src/turbovla_runtime.cpp`、`turbovla/lite_hardware_pack.py`、`tests/test_e2e_abi_consistency.py`、`tests/test_lite_hardware_pack.py`。
- 验证命令：`PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`；`python3 tools/run_runtime_csim.py`；`python3 tools/run_e2e_csim.py --fixture-dir tests/data/lite_parameter_pack_qat`；`python3 tools/validate_vivado_baseline.py hardware/vivado_kr260/report_manifest.json`。
- 远程 HLS/Vivado 命令、工具版本、原始日志、报告和 checksum：`hardware/vivado_kr260/reports/t015/README.md` 及同目录文件。
- package 运行命令：`PATH=/home/frank/AMD/vivado/2025.01/2025.1/Vivado/bin:$PATH python3 tools/package_kr260.py hardware/vivado_kr260/build/turbovla_kr260.xsa build/package_kr260_t015`。
- task branch：`task/T015-state-scale-contract`；PR #4 仍为 Draft，未满足 `done` 所需的合并条件。

## Thermo-nuclear review

- 日期：2026-09-22；reviewer：Codex
- 范围：`origin/main...2b88e7f` PR #4 diff，含 T015 ABI/HLS/runtime/package 变更及其测试边界
- 结果：`PASS_WITH_DEVICE_AND_PR_GATES`; 未发现新的代码结构 blocking finding
- 结构检查：无因 T015 新增而超过 1,000 行的源码文件；state-scale 逻辑保持在 model contract/HLS/runtime canonical boundary；独立 co-sim case 由 runner 进程隔离，未增加共享全局状态或 one-off 分支
- 分支/边界检查：v0.2 rejection、非法 scale 和 instruction gate 均 fail-fast；没有 CPU inference fallback、替代 FPGA target 或 DPU 路径
- 发现处置：`.119` 无 XRT headers 和 PR 仍为 Draft 是外部 gate；板端 `.120` action parity 已通过，未通过代码改动规避环境问题
- 证据：本目录 HLS/Vivado 日志、`timing_summary.rpt`、`utilization.rpt`、`power.rpt`、`cdc.rpt`、`turbovla_lite_e2e_csynth.rpt`、package manifest；功能日志 checksum 见 README 上文
