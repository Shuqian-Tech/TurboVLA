# TurboVLA FPGA Agent Instructions

## Initialization Is Mandatory

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
- Vivado post-route timing, resource reports, and bitstream generation are required gates.
- HLS is optional for kernel generation; Vivado remains the system integration, synthesis, implementation, and bitstream tool.
- When the `fpl26` MCP is available and direct Vivado invocation is inconvenient, it may be used for KR260 operations. The MCP must not change the target platform or bypass recorded Vivado reports. If it is unavailable, use repository-local Vivado Tcl/HLS scripts.

## KR260 Access

- SSH endpoint for the target board: `ubuntu@192.168.68.123`.
- Do not store passwords, private keys, or other credentials in the repository.
- Before any hardware task, verify SSH reachability with a short, non-mutating command and record the result in the task evidence.
- Vivado Hardware Manager is expected to be connected to the KR260 target. Hardware tasks must verify the active target/device and JTAG connection before programming or capturing reports.
- If Hardware Manager is disconnected, stop the hardware step and record the blocker; do not silently switch to another board or a software-only substitute.
- The board SSH endpoint and Hardware Manager connection are environment facts, not permission to perform destructive board operations.

## Task, Branch, and PR Policy

- Every task is represented by its own file under `docs/tasks/`.
- Every task must be implemented on its own branch. Use the branch form `task/<task-id>-<short-slug>`, for example `task/T005-gemm-ip`.
- Every task requires its own pull request. Do not combine unrelated tasks into one PR.
- The task file must record branch name, PR link/number, status, changed files, validation commands, and acceptance evidence.
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

No task is complete while a blocking thermo-nuclear finding remains unresolved or explicitly waived by the project owner.

## Status Update Protocol

After each task transition, update all applicable records atomically:

1. The task file under `docs/tasks/`.
2. The active Sprint file under `docs/sprint/`.
3. `docs/development_status.md`.

Status values are `planned`, `in_progress`, `blocked`, `in_review`, `accepted`, or `done`. A status update must include evidence, not only a claim.

## MVP Boundary

The current MVP is TurboVLA-Lite: one view, 128x128 input, FPGA-friendly tiny CNN student, instruction embedding table, two-layer fusion/gated fusion, and a 12x7 action MLP. The original DINOv3/BERT checkpoint is a teacher/reference, not an MVP runtime dependency. Any expansion beyond this boundary requires a new task and updated acceptance criteria.
