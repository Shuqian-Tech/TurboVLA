# TurboVLA-Lite Acceptance Review

Review date: 2026-09-20
Reviewer: Codex  
Target: AMD Kria KR260/K26 only  
Verification mode: `software_only`

## Result

`BLOCKED_BY_ACCEPTANCE_GATES`

The software path has deterministic reference, student smoke training,
parameter-pack export, portable and Vitis HLS C kernel simulations, runtime
model, replay, and safety replay evidence. GEMM/Conv, action MLP, and staged
gated-fusion RTL co-simulation have passed. The project is not marked
`accepted` or `done` because independent task PRs are not yet created, formal
teacher/LIBERO training data is absent, the current checkout cannot independently
verify the other machine's current-source Vivado bitstream/XSA and build log,
and KR260 hardware bring-up is `not_run`.

## Thermo-Nuclear Review

- No new file exceeds the 1k-line decomposition gate.
- T005/T006 share the T005 GEMM core; fusion/action does not duplicate a MAC implementation.
- Tensor/register ownership remains in the T001 contract and its KR260 register-map validator.
- Runtime, safety, replay, and report generation have explicit boundaries; no CPU inference fallback was added.
- Remaining blocking findings are environment or missing-evidence gates, not waived code findings.

## Evidence

The machine-readable artifact and task status index is
`docs/release/turbovla_lite_release_manifest.json`. The recorded software
checks include Python unit tests, `g++ -Werror` C simulations, Vitis HLS C
simulation, ruff checks, contract/register-map validation, deterministic replay,
and 1000-cycle safety replay. The local Vivado report manifest and archived
bitstream/XSA remain software-only artifacts; because the current-source build
log and non-ignored outputs from the other machine are not present here, they
are not treated as independently reproducible release evidence. The board
probe found the `k26-starter-kits` overlay, no TurboVLA device-tree nodes, and
zero local JTAG targets. Hardware Manager, TurboVLA bitstream load, PL DMA,
hardware inference, and KR260 30-minute stability remain `not_run`.
