# T005：实现 INT8 GEMM/Conv IP

- 状态：`in_review`
- Sprint：Sprint 2
- 分支：`task/T005-gemm-conv-ip`
- PR：待创建
- 依赖：T004
- 验收 skill：`thermo-nuclear-code-quality-review`

## 当前执行记录

- 开始时间：2026-09-19
- 当前分支：`task/T005-gemm-conv-ip`
- kernel：`hardware/hls/gemm/gemm.{h,cpp}`，统一 INT8 GEMM 与 1x1 Conv wrapper
- C simulation：`hardware/hls/gemm/tb_gemm.cpp`，覆盖正常矩阵、1x1 Conv、非法 shape
- 构建入口：`tools/run_gemm_csim.py`
- 平台边界：kernel 只面向 KR260/K26；无动态内存、CPU fallback 或其他 board 分支

## 验证记录

- `python3 tools/run_gemm_csim.py`：通过，输出 `gemm/conv C simulation passed`
- 编译参数：`g++ -std=c++17 -O2 -Wall -Wextra -Werror`
- `ruff check hardware/hls/gemm tools/run_gemm_csim.py`：通过（`.venv` ruff 0.16.8）
- `/home/frank/AMD/vivado/2025.01/2025.1/Vivado/bin/vivado -version`：通过（v2025.1）
- `TURBOVLA_LOCALE_ROOT=/tmp/turbovla-repo-locale tools/run_vitis_hls.sh hardware/hls/gemm/vitis_hls.tcl`：通过，Vitis HLS C simulation 输出 `gemm/conv C simulation passed`
- `TURBOVLA_HLS_SYNTH=1 tools/run_vitis_hls.sh hardware/hls/gemm/vitis_hls.tcl`：GEMM/Conv synthesis、IP export 通过
- GEMM/Conv RTL co-simulation：`COSIM 212-1000 PASS`；reports 在 `build/hls/gemm/{gemm_solution,conv1x1_solution}/sim/report/`
- Vivado system synthesis/implementation/post-route：当前源码 KR260 全量重建通过；bitstream/XSA 和 post-route 报告位于 `hardware/vivado_kr260/build/`
- 硬件 bring-up：`not_run`

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_PR_GATE`
- 结构检查：GEMM 是唯一计算核心，Conv 只复用 GEMM；固定上界、状态码和 testbench 分离，文件均远低于 1k 行
- code-judo 检查：没有复制第二套 MAC kernel；1x1 Conv 通过统一 row-major GEMM 入口复用边界和量化路径
- blocking findings：无代码 blocking finding；独立 PR 尚未创建，gated-fusion 之外的 HLS/Vivado evidence 已补齐
- disposition：进入 `in_review`，等待独立 PR 和 reviewer 确认

## 任务要求

使用 HLS C++ 或 SystemVerilog 实现可复用 INT8 GEMM/Conv kernel，覆盖 tiny CNN、projection 和 action MLP 的矩阵乘。支持 AXI4-MM/AXI4-Stream 规定的数据路径和 AXI4-Lite 控制接口。

## 交付物

- kernel source；
- C testbench；
- HLS synthesis/co-simulation report；
- IP package；
- resource/latency baseline。

## 详细验收

- C simulation 与 T002 INT8 reference 对齐；
- HLS co-simulation 通过；
- II、latency、DSP、BRAM、URAM、LUT、FF 已记录；
- 没有动态内存、不可综合代码或 CPU fallback；
- thermo-nuclear review 检查 tile/parallelism abstraction 是否导致复杂分支或重复 kernel；
- PR 包含报告和可复现构建命令。
