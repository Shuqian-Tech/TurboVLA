# T011：完成机器人闭环与稳定性测试

- 状态：`planned`
- Sprint：Sprint 3
- 分支：`task/T011-closed-loop-stability`
- PR：待创建
- 依赖：T009、T010
- 验收 skill：`thermo-nuclear-code-quality-review`

## 任务要求

将 KR260 action 输出接入回放或真实机器人控制闭环，覆盖动作限幅、超时、非法值、急停和连续运行稳定性。

## 交付物

- replay/robot control node；
- safety policy；
- 30 分钟稳定性日志；
- latency、功耗和温度记录；
- 任务成功率报告。

## 详细验收

- 连续运行 30 分钟无 DMA 错误、NaN、超时或动作漂移；
- action limit、timeout 和 emergency stop 都有可触发测试；
- 机器人通信断开时 PL 不会继续输出未确认动作；
- 目标 LIBERO 子集成功率达到批准阈值；
- thermo-nuclear review 确认安全逻辑位于正确边界，没有散落在多个 callback 中；
- PR 附带原始日志和故障注入结果。
