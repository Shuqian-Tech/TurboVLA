# T013: PL inference chain and PS runtime end-to-end alignment

- Status: `in_review`
- Branch: `task/T013-pl-runtime-e2e`
- Pull request: [#2](https://github.com/Shuqian-Tech/TurboVLA/pull/2) (`ready for review`)
- Platform: AMD Kria KR260/K26 (`xck26-sfvc784-2LV-c`)
- Hardware bring-up: `passed_30_min` (17,019 complete 84-value parity iterations)
- Started: 2026-09-20

## Objective

Complete the fixed-shape image/state/instruction-to-action inference path in PL, connect it to a real PS buffer/MMIO runtime boundary, and automatically compare all 84 action values with the Python INT8 reference. No neural operation may fall back to the PS.

## Scope

- Add one canonical end-to-end HLS top for image preprocessing, tiny CNN, visual projection, instruction lookup, two gated-fusion layers, state projection, action MLP, and PL action dequantization.
- Use one coherent DDR transport model: HLS AXI4-MM masters read/write PS-owned contiguous buffers; AXI-Lite controls the top. Remove the unconnected AXI DMA path from the Vivado design.
- Add a PS runtime backend with explicit physical addresses, 64-byte alignment, cache flush/invalidate, register programming, start/poll/timeout/error handling, and action readback.
- Add deterministic action parity tests against the checked-in golden bundle and parameter pack.
- Run high-memory HLS/Vivado jobs on `frank@192.168.68.119` from an isolated worktree created from the pushed GitHub branch.

## Acceptance Criteria

- Input ABI is exactly image `uint8[1,1,3,128,128]`, state `int16[1,8]`, and instruction ID `uint16[1]`; output is action `float32[1,12,7]`.
- HLS C simulation checks all 84 action values against the Python INT8 golden with recorded maximum and mean absolute error thresholds.
- RTL co-simulation passes for the same vector on the exact accepted commit.
- Vivado block design contains the complete inference top, its AXI-Lite control, DDR master ports, and interrupt; there is no unused AXI DMA transport.
- Vivado synthesis, implementation, post-route timing, resource, power, CDC, bitstream, and XSA results are recorded for KR260/K26. For the first board bring-up, the project owner explicitly made WNS/TNS reporting-only on 2026-09-21: any negative WNS must be recorded as `bringup_owner_waived`, never as timing clean or release timing closure. Timing closure remains required before release acceptance.
- Runtime fake-MMIO tests prove buffer layout, address programming, cache direction, successful completion, contract rejection, and timeout/error behavior without CPU inference.
- KR260 execution evidence is recorded separately and must remain `not_run` unless a compatible `.bit.bin`/device-tree overlay and non-destructive load procedure are available.
- The task branch and PR pass `thermo-nuclear-code-quality-review` with every blocking finding resolved or owner-waived.

## Changed Files

- `hardware/hls/e2e/`: complete fixed-shape HLS top, model layout, parity testbench, and Vitis HLS flow.
- `turbovla/lite_hardware_pack.py`, `tools/export_lite_hardware_fixture.py`: reproducible PL model/fixture export.
- `runtime/`: contiguous arena, MMIO, cache maintenance, polling, version/error/sequence validation, and fake-device tests.
- `hardware/contracts/turbovla_lite_contract.json`, `hardware/vivado_kr260/register_map.json`: v0.2 arena ABI.
- `hardware/vivado_kr260/`: single-IP KR260 block design with one AXI4-MM path and interrupt.

## Validation Evidence

- `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`: 18 tests passed.
- `PYTHONPATH=. .venv/bin/python tools/run_e2e_csim.py`: 84 action values passed, max absolute error `1.86265e-09`, mean absolute error `4.14556e-10`.
- `PYTHONPATH=. .venv/bin/python tools/run_runtime_csim.py`: arena/MMIO/cache path passed.
- `TURBOVLA_HLS_SYNTH=1 tools/run_vitis_hls.sh hardware/hls/e2e/vitis_hls.tcl`: Vitis HLS 2025.1 C simulation, synthesis, IP export, and exact-vector RTL co-simulation passed on `xck26-sfvc784-2LV-c` from exact commit `dc31221`. RTL completed `2/2`, C post-check parity and invalid-instruction gate passed, runner exit code was 0, elapsed time was `1h46m20s`, and peak XSIM RSS was `111802040 KB`. Evidence: [HLS/Vivado report index](../../hardware/vivado_kr260/reports/t013/README.md).
- HLS synthesis/IP export and the 200 MHz Vivado backend completed from commit `64acaa9`: post-route WNS `+0.002 ns`, TNS `0`, WHS `+0.010 ns`, THS `0`; bitstream and XSA were generated with zero errors/critical warnings. LUT `29.29%`, FF `16.46%`, DSP `13.46%`, BRAM `5.21%`, and estimated power `3.185 W`.
- KR260 package load, JTAG AXI-Lite read, non-starting runtime probe, and full PL inference passed. All 84 action values matched the golden vector with max absolute error `1.86265e-09` and mean absolute error `4.14556e-10`. The exact `dc31221` runtime then completed 17,019 parity-checked iterations over 30 minutes with no timeout, PL error, non-finite action, mismatch, disconnect, or reset. Final Temp_PL was `31.8 C`, board power was `3.58 W`, FPGA manager remained `operating`, overlay remained `applied`, and PL0 remained enabled at 199.998 MHz. Evidence: [KR260 board bring-up](../../hardware/vivado_kr260/reports/t013_board_bringup.md).
- A follow-up 12-sample live load capture ran one full PL inference per sample: `12/12` passed, `Temp_PL` stayed in `29.003-31.396 C`, INA260 board power in `3.350-3.440 W`, `VCCINT` in `719-721 mV`, and `VCCBRAM` in `841-846 mV`; FPGA manager, overlay, and PL0 clock state stayed healthy. Evidence: [live board sample](../../hardware/vivado_kr260/reports/t013_board_live_sample.md).
- Board lockup root cause: the old `generic-uio` overlay referenced PL0 but did not enable it (`CLKACT=0`, `pl0_ref enable_count=0`). Commit `ee22fc1` adds an `xlnx,fclk` clock consumer; a cold overlay reload from an explicitly disabled PL0 state produced `enable_count=1`, restored JTAG control reads, and passed inference without manual register writes.
- `PYTHONPATH=. .venv/bin/python tools/validate_mvp_contract.py`, `tools/validate_kr260_block_manifest.py`, Vivado baseline validation, changed-file `ruff`, all repository JSON parsing, source/documentation `git diff --check`, and AddressSanitizer/UndefinedBehaviorSanitizer C++ runs passed. Machine-generated `.rpt` files are preserved byte-for-byte and excluded from whitespace normalization.
- Timing gate contract update (2026-09-21, project owner): first-board bring-up may proceed regardless of final WNS/TNS so the PS-to-PL path can be exercised. Negative slack is `bringup_owner_waived`, is not timing clean, and remains a release blocker to be optimized after the path is operational.
- Cross-machine alignment: local, isolated high-memory-host, and KR260 runtime worktrees used GitHub commit `dc31221` for final verification. Pre-existing remote T012 edits remain preserved at `archive/remote-t012-wip-20260920` (`52bcb81`); stale report/status changes were not merged.

## Thermo-Nuclear Review

- Review date: 2026-09-21.
- Reviewer/agent: Codex.
- Review result: `PASS`; no blocking finding remains. The task is `in_review` pending PR review/merge and is not marked `done`.
- PR scope: 39 changed files against `task/T012-final-acceptance`; 2,307 insertions and 219 deletions before final evidence. No source file crosses 1,000 lines; the new HLS top is 344 lines and the board runtime is 275 lines.
- Structural/code-judo result: one canonical aligned arena, one end-to-end HLS top, and one AXI-Lite/AXI4-MM path replace the disconnected DMA and multi-kernel composition. `RegisterIo` and `CacheMaintenance` keep host tests and board I/O behind explicit boundaries without duplicating inference or adding a CPU fallback.
- Abstraction/branching/boundary result: no alternate board target, DPU path, silent CPU inference, scattered platform branch, cast-heavy generic layer, or >1k-line file was introduced. PS code remains limited to XRT buffer ownership, cache synchronization, UIO MMIO, polling, validation, and action readback. Cross-language ABI duplication is guarded by contract consistency tests.
- Finding 1: the v0.2 contract initially allowed instruction IDs through 65534 while the PL table has 256 entries. Disposition: fixed to `0..255` in `dc31221` and covered by contract and ID-256 tests.
- Finding 2: `PlArenaExecutor::load_model()` initially returned contract mismatch for an invalid arena. Disposition: fixed in `dc31221` to return invalid buffer and covered by the runtime test.
- Finding 3: the HLS parity test could let a non-finite action evade the numeric threshold. Disposition: fixed in `dc31221` with explicit finite checks; the same test also exercises invalid instruction ID 256.
- Evidence: [HLS/Vivado reports](../../hardware/vivado_kr260/reports/t013/README.md), [KR260 bring-up and stability](../../hardware/vivado_kr260/reports/t013_board_bringup.md), 18-test unit log from the validation command above, C++ parity/runtime logs, sanitizer pass, and scoped lint/contract/JSON checks.
