# T011：完成机器人闭环与稳定性测试

- 状态：`in_progress`
- Sprint：Sprint 3
- 分支：`task/T011-closed-loop-stability`
- PR：待创建
- 依赖：T009、T010
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T011-closed-loop-stability`
- safety policy：`turbovla/safety.py`
- replay runner：`tools/run_stability_replay.py`
- 软件报告：`tests/data/lite_stability_report.json`
- verification mode：`software_only`；真实机器人/开发板：`not_run`

## 验证记录

- `python3 tools/run_stability_replay.py --cycles 1000 --output tests/data/lite_stability_report.json`：通过
- accepted cycles：`1000/1000`
- max action drift：`0.0`
- fault injection：NaN、emergency stop、communication disconnect、frame timeout 均按预期拒绝
- `ruff check turbovla/safety.py tools/run_stability_replay.py tests/test_safety.py`：通过
- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`：9 tests 通过
- 30 分钟实机稳定性、温度、功耗和机器人成功率：`not_run`

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_HARDWARE_GATE`
- 结构检查：SafetyPolicy 集中处理限幅/NaN/timeout/急停/通信状态，replay runner 只负责编排和报告
- code-judo 检查：没有把安全分支散落到多个 callback；所有拒绝原因统一为 SafetyDecision
- blocking findings：无代码 blocking finding；实机 30 分钟闭环和真实机器人通信尚未运行
- disposition：保留 `in_progress`，待 board-ready 后补充硬件稳定性 gate

## 任务要求

将 KR260 action 输出接入回放或真实机器人控制闭环，覆盖动作限幅、超时、非法值、急停和连续运行稳定性。

## 交付物

- replay/robot control node；
- safety policy；
- 30 分钟稳定性日志；
- latency、功耗和温度记录；
- 任务成功率报告。

## 详细验收（software_only；实机闭环 deferred）

- 软件 replay 连续运行 30 分钟无 DMA model 错误、NaN、超时或动作漂移；
- action limit、timeout 和 emergency stop 都有可触发测试；
- 机器人通信断开时 PL 不会继续输出未确认动作；
- 目标 LIBERO 子集软件回放成功率达到批准阈值；
- thermo-nuclear review 确认安全逻辑位于正确边界，没有散落在多个 callback 中；
- PR 附带原始软件日志和故障注入结果；真实机器人/开发板闭环标记为 `not_run`。
