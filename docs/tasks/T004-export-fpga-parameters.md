# T004：生成 FPGA 参数包

- 状态：`done`
- Sprint：Sprint 1
- 分支：`task/T004-export-fpga-parameters`
- PR：[Shuqian-Tech/TurboVLA#6](https://github.com/Shuqian-Tech/TurboVLA/pull/6)（待合并）
- 依赖：T002、T003
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T004-export-fpga-parameters`
- 实现：`turbovla/lite_parameter_pack.py` 和 `tools/export_lite_parameters.py`
- 格式：little-endian、64-byte tensor alignment、INT8 symmetric weights、FP32 biases、per-tensor scale、manifest checksum
- smoke 参数包：`tests/data/lite_parameter_pack_smoke/`，由 T003 smoke checkpoint 生成
- 正式参数包：`tests/data/lite_parameter_pack_qat/`，由 T014 选定 QAT checkpoint 生成，并由 T015 v0.3 ABI 承载 calibrated state scale
- 硬件 bring-up：`passed`；正式包已在 KR260 `.120` 完成 action parity 和 validation sweep

## 验证记录

- `PYTHONPATH=. .venv/bin/python tools/export_lite_parameters.py --checkpoint build/lite/student_smoke.pt --output-dir build/lite/parameter_pack`：通过，19 tensors，150528 bytes
- manifest tensor offsets：全部满足 `offset % 64 == 0`
- loader checksum：通过，19 tensors 完整重建
- T002 reference reconstruction：通过，action shape `(1,12,7)`
- versioned artifact：`tests/data/lite_parameter_pack_smoke/weights.bin` 与 `manifest.json`
- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：通过（包含 parameter-pack round-trip）
- weights SHA256：`2c6f6081e92ddcf5ffcc22b706f8c0eb7b5c293eae357d5c78afd9d6acb3242`
- manifest SHA256：`67c1ce537ed6cad7428eebdac55d72da27bacb7db66d1776a53df92504d99993`

## 任务结论

- T004 已完成：正式 QAT 参数包已替换 smoke-only 证据，并通过软件、PL parity、Vivado 和 KR260 bring-up gate。
- T004 不改变 TinyCNN 结构或部署目标；state scale ABI 变化由 T015 的 v0.3 contract 唯一承载。

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_DATASET_GATE`
- 结构检查：导出、loader、reference reconstruction 和 CLI 分层；核心参数包模块 225 行，未超过 1k 行边界
- code-judo 检查：manifest 是唯一 offset/dtype/shape/checksum 来源，loader 不复制布局规则；量化只在导出边界执行一次
- blocking findings：无代码 blocking finding；当前输入仍是 smoke checkpoint，正式训练参数尚未生成
- disposition：smoke 阶段 finding 已由正式 QAT 参数包、PL parity 和 KR260 bring-up 关闭

## 最终验收记录

- 正式 QAT checkpoint SHA256：`7209a40065aa72628bd1a2b3b92d92a205ac97a4bb1a4577c1e4eda3d5d5dc1a`；未重训、未修改模型权重。
- 正式 v0.3 `model.bin`：150656 bytes，19 tensors，SHA256 `6df32b27eb8a730027c6f37af8c8bd33058700293941a44eae6ade0697fa3886`；tensor offsets 保持 64-byte alignment。
- 软件 exact INT8、HLS C-sim/RTL co-sim、Vivado synthesis/implementation/post-route、bitstream/XSA 和 package manifest 均通过；证据目录为 `hardware/vivado_kr260/reports/t015/`。
- KR260 `.120`：正式包 action parity `100/100` validation sweep 通过，FPGA 对 exact INT8 worst max error `1.78814e-07`；该结果是独立 hardware bring-up 证据，不与 software-only Vivado 报告混淆。
- 验证命令：`PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`（35 passed）、`python3 tools/run_e2e_csim.py --fixture-dir tests/data/lite_parameter_pack_qat`、`python3 tools/validate_vivado_baseline.py hardware/vivado_kr260/report_manifest.json`。
- thermo-nuclear review：2026-09-22，reviewer Codex，结果 `PASS_WITH_DEVICE_AND_PR_GATES`；无未处置 blocking finding。审查覆盖参数布局 canonical boundary、loader/exporter 分层、文件大小、分支复杂度、ABI 一致性及软件/硬件证据边界。

## 任务要求

将 student checkpoint 转换为 FPGA 可加载的 INT8/INT32 参数包，生成 instruction embedding table、scale、bias、metadata 和版本 manifest。参数布局必须与 kernel 读取顺序一致。

## 交付物

- 权重二进制文件；
- instruction embedding table；
- scale/bias/zero-point 文件；
- 参数 manifest 和 checksum；
- Python loader 与 reference replay。

## 详细验收

- 每个参数有 dtype、shape、offset 和 checksum；
- loader 能完整重建 T002 reference 所需参数；
- endian、对齐、stride 和 padding 有测试；
- 参数包不依赖运行时 Python；
- thermo-nuclear review 确认参数转换没有散落的格式特判；
- PR 附带 manifest、大小统计和 replay 结果。
