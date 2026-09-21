# T013 HLS and Vivado Reports

## Source Revisions

- HLS synthesis and final co-simulation source: `dc31221`
- Vivado synthesis/implementation source: `64acaa9`
- `hardware/hls/e2e/e2e.cpp`, `e2e.h`, and `model_layout.h` are identical
  between these revisions. Later commits change the bring-up gate, runtime,
  package, testbench, and evidence only.
- Target: `xck26-sfvc784-2LV-c`, Vivado/Vitis HLS 2025.1.

## HLS Synthesis

[`turbovla_lite_e2e_csynth.rpt`](turbovla_lite_e2e_csynth.rpt) records a
5.00 ns target, 3.798 ns estimated clock, maximum latency 3,817,788 cycles
(19.089 ms), and estimated use of 24 BRAM18K, 148 DSP, 40,942 FF, and 49,961
LUT.

Exact-vector RTL co-simulation for `dc31221` passed on the high-memory host:

- [`turbovla_lite_e2e_cosim.rpt`](turbovla_lite_e2e_cosim.rpt): Verilog
  status `Pass`.
- [`t013_hls_cosim_summary.txt`](t013_hls_cosim_summary.txt): RTL simulation
  `2/2`, C post-check parity max absolute error `1.86265e-09` and mean
  absolute error `4.14556e-10`, invalid-instruction gate passed, runner exit
  code 0.
- Elapsed time was `1h46m20s`; peak XSIM RSS was `111802040 KB`.

## Vivado Post-Route

- [`timing_summary.rpt`](timing_summary.rpt): 200 MHz, WNS `+0.002 ns`, TNS
  `0`, WHS `+0.010 ns`, THS `0`; all specified timing constraints met.
- [`utilization.rpt`](utilization.rpt): LUT `29.29%`, FF `16.46%`, DSP
  `13.46%`, BRAM `5.21%`, URAM `0%`.
- [`power.rpt`](power.rpt): estimated total on-chip power `3.185 W`.
- [`cdc.rpt`](cdc.rpt): post-route single-clock CDC report.

The generated bitstream and XSA are not committed. Their hashes and the board
package hashes are recorded in
[`../t013_board_bringup.md`](../t013_board_bringup.md).
