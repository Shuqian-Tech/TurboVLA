# T015 KR260/software evidence

All software build artifacts in this directory were produced from commit
`2b88e7f` in the isolated worktree `/home/frank/TurboVLA-codex-T015-b3761ce`
on `frank@192.168.68.119`. They are not board-execution evidence.

## HLS and RTL co-simulation

- Case 0 was run as one independent XSIM process. It passed with
  `max_abs_error=1.19209e-07` and `mean_abs_error=1.98128e-08`.
- Cases 1 through 5 were each run as separate XSIM processes and all passed:
  invalid instruction ID, v0.2 request rejection, v0.2 model rejection,
  non-positive state scale rejection, and non-finite state scale rejection.
- Case 0 XSIM peak memory was `111802256 KB`; this exceeds the previous 96 GiB
  target, although the 162 GiB build host completed without swap or failure.
- HLS log checksums: case 0
  `24900c1e5d050fa0509b505cc4c10c46d339d5fda8ebb2459f7fd538bea59369`;
  cases 1-5
  `e45d776b545fc7803583693df6e2e499c563e45d7c05457d3cebc6f9ef182433`.

## Vivado KR260 build

- Device: `xck26-sfvc784-2LV-c`.
- Post-route timing: WNS `+0.01316635683178902 ns`, TNS `0`, WHS `+0.010 ns`,
  THS `0`; route status had zero unrouted, partially routed, or overlapping
  nets.
- Utilization: LUT `29.23%`, FF `16.55%`, DSP `13.46%`, BRAM `5.21%`, URAM
  `0%`.
- Estimated on-chip power: `3.259 W` (`2.956 W` dynamic, `0.304 W` static).
- HLS synthesis estimated clock period is `3.798 ns`; maximum latency is
  `3,817,800` cycles.
- Bitstream and XSA were generated. Their checksums are recorded in the
  package manifest and task file.

## KR260 package and target enumeration

`package_kr260.py` completed with control base `0xa0000000` and PL clock
`200000000 Hz`. Package artifact checksums are in `manifest.json`.

Vivado Hardware Manager connected non-destructively to
`127.0.0.1:3121/xilinx_tcf/Xilinx/XFL13WUMT00XA` and enumerated
`xck26_0 arm_dap_1`.

The board endpoint `amd-edf@192.168.68.123` returned `No route to host` from
both the local host and the build host on 2026-09-22. No package was loaded,
no UIO/XRT probe was run, and no action parity claim is made. Hardware
bring-up therefore remains `not_run`.

The board runtime compile was attempted on the build host and stopped because
that host has no XRT development headers (`xrt/xrt_bo.h`); this is an
environment limitation, not a board result. The runtime must be compiled in
the board's XRT-enabled environment before full parity testing.

