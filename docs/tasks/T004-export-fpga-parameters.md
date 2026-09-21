# T004：生成 FPGA 参数包

- 状态：`in_progress`
- Sprint：Sprint 1
- 分支：`task/T004-export-fpga-parameters`
- PR：待创建
- 依赖：T002、T003
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T004-export-fpga-parameters`
- 实现：`turbovla/lite_parameter_pack.py` 和 `tools/export_lite_parameters.py`
- 格式：little-endian、64-byte tensor alignment、INT8 symmetric weights、FP32 biases、per-tensor scale、manifest checksum
- smoke 参数包：`tests/data/lite_parameter_pack_smoke/`，由 T003 smoke checkpoint 生成；正式 student checkpoint 到位后使用相同入口替换
- 硬件 bring-up：`not_run`；参数包校验不依赖 KR260 实机

## 验证记录

- `PYTHONPATH=. .venv/bin/python tools/export_lite_parameters.py --checkpoint build/lite/student_smoke.pt --output-dir build/lite/parameter_pack`：通过，19 tensors，150528 bytes
- manifest tensor offsets：全部满足 `offset % 64 == 0`
- loader checksum：通过，19 tensors 完整重建
- T002 reference reconstruction：通过，action shape `(1,12,7)`
- versioned artifact：`tests/data/lite_parameter_pack_smoke/weights.bin` 与 `manifest.json`
- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：通过（包含 parameter-pack round-trip）
- weights SHA256：`2c6f6081e92ddcf5ffcc22b706f8c0eb7b5c293eae357d5c78afd9d6acb3242`
- manifest SHA256：`67c1ce537ed6cad7428eebdac55d72da27bacb7db66d1776a53df92504d99993`

## 当前验收边界

- T004 仍为 `in_progress`：当前参数包来自 smoke checkpoint，不代表正式 LIBERO student 参数
- Vivado/HLS 和板卡加载属于后续任务，当前不宣称硬件验证

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_DATASET_GATE`
- 结构检查：导出、loader、reference reconstruction 和 CLI 分层；核心参数包模块 225 行，未超过 1k 行边界
- code-judo 检查：manifest 是唯一 offset/dtype/shape/checksum 来源，loader 不复制布局规则；量化只在导出边界执行一次
- blocking findings：无代码 blocking finding；当前输入仍是 smoke checkpoint，正式训练参数尚未生成
- disposition：保留 `in_progress`，待 T003 正式 checkpoint 后重新导出并执行最终 acceptance

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
