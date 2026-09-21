# T003：训练 TurboVLA-Lite student

- 状态：`in_progress`
- Sprint：Sprint 1
- 分支：`task/T003-train-lite-student`
- PR：待创建
- 依赖：T001、T002
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T003-train-lite-student`
- 模型：`turbovla/lite_student.py`，固定 128x128、32 tokens、hidden 128、12x7 action
- 训练入口：`tools/train_lite_student.py`，支持 external NPZ 数据和显式 `--smoke` 模式
- 配置：`configs/turbovla_lite_student.json`
- smoke 产物：`tests/data/lite_student_smoke_report.json`；checkpoint 留在本地 `build/lite/student_smoke.pt`
- 数据状态：真实 LIBERO teacher checkpoint、蒸馏特征和目标子集尚未提供；当前只完成确定性 smoke training
- 硬件 bring-up：`not_run`；训练任务不以 KR260 实机为前置条件

## 验证记录

- `uv venv .venv --python 3.12`：通过
- `uv pip install --python .venv/bin/python 'torch>=2.3,<3'`：通过，安装 PyTorch 2.14.0
- `uv pip install --python .venv/bin/python 'numpy>=1.26,<2'`：通过，安装 NumPy 1.26.4
- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：通过，6 tests
- `PYTHONPATH=. .venv/bin/python tools/train_lite_student.py --smoke --steps 3 --batch-size 4 ...`：通过
- smoke parameter count：`148948`
- smoke action L1：`0.0628083 -> 0.0491720`
- smoke teacher-action L1：`0.0631098 -> 0.0490225`
- smoke checkpoint reload：通过，输出 shape 为 visual `(1,32,128)`、action `(1,12,7)`
- smoke report SHA256：`46d929f1f1bcdb8bdb6569bb192726d7f14d3f9fe70da173392d97b0a2677d19`

## 当前验收边界

- T003 尚未进入 `in_review`：缺少真实 teacher/student 训练数据、LIBERO 子集成功率和正式 checkpoint hash
- 不使用 CPU inference fallback；训练脚本缺少 PyTorch 时直接报依赖错误，推理仍由 T002 reference/后续 PL kernel 定义

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_DATASET_GATE`
- 结构检查：模型、训练入口、配置和测试分层；最大新增实现文件 162 行，未接近 1k 行边界
- code-judo 检查：训练与推理共用 T001 shape contract，student 内部维度集中于 `LiteStudentConfig`，蒸馏项集中于一个 loss 函数
- 复杂度检查：无动态长度分支、CPU inference fallback 或散落 feature flags；`--smoke` 为显式数据模式，不影响 external dataset 路径
- blocking findings：代码无 blocking finding；真实 teacher/LIBERO 数据、正式 checkpoint 和成功率评估仍未提供
- disposition：保留 `in_progress`，待真实数据训练和正式评测后再进入完整 acceptance review

## 任务要求

使用原始 TurboVLA 作为 teacher/reference，训练 tiny CNN + fusion + action MLP student。训练目标同时包含动作监督和 teacher action/feature 蒸馏，最终 checkpoint 必须符合固定 shape 和 INT8 校准约束。

## 交付物

- student checkpoint；
- 训练配置和数据版本；
- teacher/student action 对比报告；
- 目标 LIBERO 子集评测结果；
- 量化感知训练配置。

## 详细验收

- checkpoint 可由 T002 reference 加载；
- 没有动态长度或未定义算子；
- teacher/student action MAE 达到项目 owner 预先批准的阈值；
- 记录成功率、action MAE、参数量和推理 shape；
- thermo-nuclear review 确认模型配置没有堆积临时开关和特殊 case；
- PR 附带训练命令、checkpoint hash 和评测日志。
