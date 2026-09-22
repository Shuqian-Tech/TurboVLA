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

The correct board endpoint is `amd-edf@192.168.68.120`. The earlier
`192.168.68.123` address was incorrect and is not a T015 result.

On 2026-09-22, `.120` reported FPGA manager `operating`, XRT `2.23.0`
(2026.1), and the starter overlay was unloaded. The T015 package was loaded
with `fpgautil -b ...turbovla_kr260.bit.bin -o ...turbovla_kr260.dtbo -f Full
-n full`. Loading `uio_pdrv_genirq` exposed `uio4=turbovla-lite-e2e`.

The board runtime was built on the board from the public GitHub branch at
commit `1bb98922f947d91778897da5d2f46ff0df9d182c`; binary SHA256 is
`75ad2ecf84d23d0938a84dd467debcca534141d24d3bbd79317dc13f7c16828f`.
Probe-only passed with control `0x4` and XRT arena address `0x4b1c0000`.
Full PL inference passed with action parity
`max_abs_error=1.19209e-07`, `mean_abs_error=1.98128e-08`.

Twelve independent live board invocations passed with the same parity and
`KR260_T015_LIVE_SAMPLES_PASS count=12`. No CPU inference fallback was used.

For a broader hardware check, ten uniformly spaced samples from the fixed
validation split (one per instruction ID) were exported from the same QAT
checkpoint and run on the board. All ten passed. The observed board parity
against the exported exact-INT8 expected action was:

| Sample | FPGA max abs | FPGA mean abs |
|---:|---:|---:|
| 0 | 5.96046e-08 | 1.54112e-08 |
| 11043 | 5.96046e-08 | 7.77765e-09 |
| 1227 | 5.96046e-08 | 9.89530e-09 |
| 2454 | 1.19209e-07 | 1.24703e-08 |
| 3681 | 5.96046e-08 | 8.81153e-09 |
| 4908 | 1.19209e-07 | 1.14669e-08 |
| 6135 | 5.96046e-08 | 1.10761e-08 |
| 7362 | 8.94070e-08 | 1.06603e-08 |
| 8589 | 1.78814e-07 | 1.48956e-08 |
| 9816 | 1.19209e-07 | 1.34709e-08 |

On those same ten samples, the QAT checkpoint versus exported exact-INT8
comparison was:

- action MAE: `0.1289300751` versus `0.1292744306` (`+0.0003443556`, exact
  INT8 is `0.267%` higher);
- gripper sign accuracy: `88.0734%` versus `87.15596%` (`-0.9174 pp`);
- QAT-to-exact-INT8 action difference: max `0.2504549`, mean `0.00635750`.

The ten-sample hardware result is a parity/implementation check, not a new
closed-loop accuracy estimate. The exact-INT8 output is what the FPGA
computes; the small accuracy delta above is the quantization/export delta
between the fake-QAT checkpoint and the deployed representation.

The board is therefore `action_parity=passed` for this vector. This is a
single-vector parity gate, not a replacement for the existing long-duration
stability evidence from T013.

The `.119` build host remains without XRT development headers. It is only a
software build host; do not copy the board's aarch64 XRT libraries to its
x86_64 filesystem. Use the matching x86_64 Ubuntu 22.04 XRT 2025.1 package or
build XRT from the matching source tag when host-side compilation is needed.
