# T013: PL inference chain and PS runtime end-to-end alignment

- Status: `in_progress`
- Branch: `task/T013-pl-runtime-e2e`
- Pull request: pending
- Platform: AMD Kria KR260/K26 (`xck26-sfvc784-2LV-c`)
- Hardware bring-up: `not_run`
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
- Vivado synthesis, implementation, post-route timing, resource, power, CDC, bitstream, and XSA gates are recorded for KR260/K26.
- Runtime fake-MMIO tests prove buffer layout, address programming, cache direction, successful completion, contract rejection, and timeout/error behavior without CPU inference.
- KR260 execution evidence is recorded separately and remains `not_run` until a compatible `.bit.bin`/device-tree overlay and non-destructive load procedure are available.
- The task branch and PR pass `thermo-nuclear-code-quality-review` with every blocking finding resolved or owner-waived.

## Changed Files

- Pending implementation.

## Validation Evidence

- Pending implementation.

## Thermo-Nuclear Review

- Pending implementation and PR diff.
