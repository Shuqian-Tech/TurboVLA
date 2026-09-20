# TurboVLA-Lite Acceptance Review

Review date: 2026-09-20
Reviewer: Codex  
Target: AMD Kria KR260/K26 only  
Verification mode: `software_only`

## Result

`BLOCKED_BY_ACCEPTANCE_GATES`

The software path has deterministic reference, student smoke training,
parameter-pack export, portable and Vitis HLS C kernel simulations, runtime
model, replay, and safety replay evidence. A KR260/K26 Vivado post-route
baseline, bitstream, and XSA are archived, but they predate the `tanh_q15`
negative-interpolation fix. A full rebuild is pending on another machine. The
project is not marked `accepted` or `done` because independent task PRs are not
yet created, formal teacher/LIBERO training data is absent, gated-fusion RTL
co-simulation is deferred, and hardware bring-up is `not_run`.

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
and 1000-cycle safety replay. The archived Vivado synthesis, implementation,
post-route timing, bitstream/XSA, utilization, power, and CDC run passed in
software-only mode; it must be repeated for the current source before those
artifacts are release evidence. Hardware Manager, bitstream load, hardware
inference, and KR260 30-minute stability remain `not_run`.
