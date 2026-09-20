# T005：实现 INT8 GEMM/Conv IP

- 状态：`in_progress`
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
- `vivado -version`：阻塞，仓库 wrapper 指向不存在的 `/home/frank/AMDDesignTools/2026.1/Vivado/bin/vivado`
- HLS co-simulation、synthesis、resource/latency report：`not_run`，工具环境尚未可用
- 硬件 bring-up：`not_run`

## Thermo-Nuclear Review（中间审查）

- review 时间：2026-09-19
- reviewer：Codex
- review 结果：`PASS_WITH_TOOLCHAIN_GATE`
- 结构检查：GEMM 是唯一计算核心，Conv 只复用 GEMM；固定上界、状态码和 testbench 分离，文件均远低于 1k 行
- code-judo 检查：没有复制第二套 MAC kernel；1x1 Conv 通过统一 row-major GEMM 入口复用边界和量化路径
- blocking findings：无代码 blocking finding；Vivado/HLS 工具不可执行，无法提供 HLS co-sim 和综合报告
- disposition：保留 `in_progress`，待工具链恢复后补齐 HLS 报告和 T002 数值对齐

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
