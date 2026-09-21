# TurboVLA FPGA Agent Instructions

## Initialization Is Mandatory

## 语言要求

- 所有代理回复、进度更新、验收记录和文档更新必须使用中文，即使用户使用英文提问。
- 本文件中的新增或修改内容也必须使用中文。

Every agent session working in this repository must read these documents before inspecting or changing implementation files:

1. `docs/development_status.md`
2. `docs/mvp.md`
3. `docs/sprint/README.md`
4. The active Sprint document linked by `docs/sprint/README.md`
5. `docs/tasks/README.md`
6. Every task file referenced by the active Sprint
7. `docs/vivado_flow.md`

The agent must use the latest development status, Sprint status, task status, dependencies, and acceptance criteria as the source of truth. If the status conflicts with an older design note, the status and active task contract win until explicitly updated.

## Fixed Hardware Target

- The only supported compilation and deployment target is the AMD Kria KR260/K26 FPGA platform.
- Do not add or validate alternative FPGA boards, GPUs, DPUs, Versal targets, Alveo targets, or generic device presets in the MVP workflow.
- The neural inference path must execute in FPGA PL. DPU, Vitis AI, and silent CPU inference fallback are prohibited.
- PS software is limited to I/O, ROS2, DMA, AXI-Lite control, scheduling, safety checks, and robot communication.
- Vivado post-route timing, resource reports, and bitstream generation are required software gates for the current development phase.
- HLS is optional for kernel generation; Vivado remains the system integration, synthesis, implementation, and bitstream tool.
- When the `fpl26` MCP is available and direct Vivado invocation is inconvenient, it may be used for KR260 operations. The MCP must not change the target platform or bypass recorded Vivado reports. If it is unavailable, use repository-local Vivado Tcl/HLS scripts.

## KR260 Access

- SSH endpoint for the target board: `amd-edf@192.168.68.123` (passwordless key access).
- Do not store passwords, private keys, or other credentials in the repository.
- The development board is currently available for non-destructive bring-up checks; SSH/JTAG access is not a prerequisite for software-only verification.
- During the current phase, verify the KR260/K26 target with software Vivado using HLS C simulation, co-simulation, synthesis, implementation, post-route timing, resource, power, CDC, and bitstream-generation reports.
- SSH and Vivado Hardware Manager may be used for the current hardware bring-up phase. If used, verify the active target/device and record the exact result; their absence must not block T001-T008 software acceptance.
- Do not silently claim an on-board test from a software report. Mark hardware bring-up as `not_run` only when the board or Hardware Manager is unavailable; keep board evidence separate from software-only reports.
- The board SSH endpoint and Hardware Manager connection are environment facts, not permission to perform destructive board operations. Bring-up commands must remain non-destructive unless explicitly authorized.

## Task, Branch, and PR Policy

- Every task is represented by its own file under `docs/tasks/`.
- Every task must be implemented on its own branch. Use the branch form `task/<task-id>-<short-slug>`, for example `task/T005-gemm-ip`.
- Every task requires its own pull request. Do not combine unrelated tasks into one PR.
- The task file must record branch name, PR link/number, status, changed files, validation commands, software Vivado evidence, and hardware bring-up status (`not_run` until the board is usable).
- A task cannot be marked `done` without a linked PR and recorded acceptance evidence.
- Do not edit a task's acceptance criteria to make an implementation pass. Update the task contract first and record the reason.

## Acceptance Gate

Every task acceptance must run the `thermo-nuclear-code-quality-review` skill. The review must cover the current task branch and its PR diff, and must be recorded in the task file. Follow the complete skill instructions in `/home/frank/.codex/skills/thermo-nuclear-code-quality-review/SKILL.md`.

The acceptance record must include:

- review date and reviewer/agent;
- review result and blocking findings;
- structural simplification/code-judo findings;
- file-size, abstraction, branching, and boundary checks;
- disposition of every finding;
- links to Vivado/HLS reports and functional test logs.

No task is complete while a blocking thermo-nuclear finding remains unresolved or explicitly waived by the project owner. Software acceptance must not be blocked solely by unavailable board/JTAG access; hardware claims remain prohibited until a later bring-up gate passes.

## Status Update Protocol

After each task transition, update all applicable records atomically:

1. The task file under `docs/tasks/`.
2. The active Sprint file under `docs/sprint/`.
3. `docs/development_status.md`.

Status values are `planned`, `in_progress`, `blocked`, `in_review`, `accepted`, or `done`. A status update must include evidence, not only a claim.

## MVP Boundary

The current MVP is TurboVLA-Lite: one view, 128x128 input, FPGA-friendly tiny CNN student, instruction embedding table, two-layer fusion/gated fusion, and a 12x7 action MLP. The original DINOv3/BERT checkpoint is a teacher/reference, not an MVP runtime dependency. Any expansion beyond this boundary requires a new task and updated acceptance criteria.
