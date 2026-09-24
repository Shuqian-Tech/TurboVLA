# T016 Validation Evidence

- 日期：2026-09-24
- 分支：`task/T016-alp-explorer`
- candidate：`design-ef6c7cfa8ebc`
- parent：`design-0bb51adbc2e4`
- source HEAD：`85e8b4fcd166e30a10dbdf9ced6c360d1523dab5`
- dirty source fingerprint：`1b0b69a69b270431a50f604ccb50972c218b8436314559f0a5487a4120c00c9c`
- profile：`software`
- policy result：`promote`，仅表示该 profile 的确定性 gate 全部通过

## Evaluator 结果

| Evaluator | 阶段 | 状态 | 耗时 |
|---|---|---:|---:|
| `contract` | architecture spec | passed | 0.021 s |
| `block_manifest` | RTL integration | passed | 0.021 s |
| `e2e_csim` | verification | passed | 0.813 s |
| `runtime_csim` | software loop | passed | 0.828 s |
| `replay` | software loop | passed | 0.238 s |
| `stability` | software loop | passed | 0.138 s |
| `unit_tests` | verification | passed | 3.003 s |
| `vivado_baseline` | physical report gate | passed | 0.025 s |

`replay.json` 和 `stability.json` 写入按 evaluation ID 隔离的 workspace 路径，并与
stdout/stderr 一起按 SHA256 归档。全仓单测结果为 `45 tests` 通过；其中 T016 专项
测试为 `10 tests` 通过。

## 验证命令

```bash
PYTHONPATH=. .venv/bin/python -m unittest tests.test_rtl_design_topo -v
.venv/bin/ruff check rtl_design_topo tests/test_rtl_design_topo.py
PYTHONPATH=. .venv/bin/python -m compileall -q rtl_design_topo tests/test_rtl_design_topo.py
PYTHONPATH=. .venv/bin/python -m rtl_design_topo.cli run \
  --workspace /tmp/turbovla-alp-smoke2.olxqte \
  --design-id design-ef6c7cfa8ebc \
  --profile software
git diff --check
```

## Vivado/HLS 与硬件边界

- 本次只运行 [既有 Vivado report manifest](../../../hardware/vivado_kr260/report_manifest.json)
  validator；没有重新执行 synthesis、implementation 或 bitstream generation。
- `full-vivado` profile 已配置为 explicit-only，且其 HLS gate 依赖所有便宜验证通过；
  本次 `not_run`。
- KR260 上板与机器人闭环：`not_run`。T013/T015 历史板端证据不冒充 T016 新运行。

## 失败路径证据

初版 adapter 使用 `--repeats 1`，现有 replay 工具按合同返回失败，controller 生成
`repair` decision；修正为 `--repeats 2` 后通过。专项测试同时覆盖 cheap gate 失败后
跳过 synthesis/route、timeout 进程组终止、配置依赖环拒绝和 source fingerprint 漂移拒绝。
