# TurboVLA-Lite Acceptance Review

Review date: 2026-09-21
Reviewer: Codex  
Target: AMD Kria KR260/K26 only  
Verification mode: `software_and_kr260_bringup`

## Result

`BLOCKED_BY_ACCEPTANCE_GATES`

The software path has deterministic reference, student smoke training,
parameter-pack export, portable and Vitis HLS C kernel simulations, runtime
model, replay, and safety replay evidence. T013 now adds the complete PL
inference top, PS runtime, exact-vector RTL co-simulation, KR260 bring-up, and
30-minute parity stability. The project is not marked `accepted` or `done`
because independent task PRs/final PR #1 review, formal teacher/LIBERO training
data, robot success-rate evidence, and worst-case thermal qualification remain.

## Thermo-Nuclear Review

- No new file exceeds the 1k-line decomposition gate.
- T005/T006 share the T005 GEMM core; fusion/action does not duplicate a MAC implementation.
- Tensor/register ownership remains in the T001 contract and its KR260 register-map validator.
- Runtime, safety, replay, and report generation have explicit boundaries; no CPU inference fallback was added.
- Remaining blocking findings are environment or missing-evidence gates, not waived code findings.

## Evidence

The machine-readable artifact and task status index is
`docs/release/turbovla_lite_release_manifest.json`. T013's accepted evidence is
indexed in `hardware/vivado_kr260/reports/t013/README.md` and
`hardware/vivado_kr260/reports/t013_board_bringup.md`; the follow-up live power,
temperature, rail, and clock-state capture is in
`hardware/vivado_kr260/reports/t013_board_live_sample.md`. The Vivado backend
meets the documented 200 MHz constraint with WNS `+0.002 ns`; this is a narrow
timing margin and remains a release optimization target. The board record
measured PL0 at `199.998 MHz`, 30-minute parity stability at 17,019 iterations,
and the live sample completed 12/12 additional inferences. Vivado power is an
on-chip estimate (`3.185 W`), while INA260 board power was `3.350-3.440 W` in
the live sample; these are different measurement boundaries.
