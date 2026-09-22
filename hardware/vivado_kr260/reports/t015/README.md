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

## Full 100-sample validation sweep

To close the validation-load gap, 100 unique samples were selected from the
fixed validation split with `np.linspace(0, 11043, 100, dtype=np.int64)` and
exported from checkpoint
`7209a40065aa72628bd1a2b3b92d92a205ac97a4bb1a4577c1e4eda3d5d5dc1a`. Each
fixture was run exactly once on `amd-edf@192.168.68.120` with
`run_at_scale.py --slots 1 --strategy fifo`; serialization is required because
the board has one shared UIO/XRT execution path.

- Board invocations: `100/100` returned success; all 100 logs contained
  `stage=pl_return result=0` and an action parity line.
- End-to-end latency: `77,073..78,647 us`, mean `77,448.69 us`, p95
  `78,439.9 us`; measured whole-path throughput `12.9118 inference/s`.
- FPGA-to-exported-exact-INT8 parity: worst max error `1.78814e-07`; worst
  mean error `2.39594e-08`, below the `1e-5`/`1e-6` gates.
- Full-window sensor capture (573 samples at approximately 250 ms): INA260
  board power `3.64..4.09 W` (mean `3.731 W`), PL temperature
  `25.024..28.490 C` (mean `26.878 C`), `/proc/loadavg` 1-minute load
  `1.02..2.06` (mean `1.557`), and available RAM `3,481.7..3,497.9 MiB`.

The load value is Linux load average, not a per-core utilization percentage;
the raw sensor capture is preserved for audit. This is the real 100-sample
validation sweep and supersedes the earlier same-fixture repetition used only
for a coarse load range. The aggregate report, scheduler summary, and raw
sensor CSV are [`validation100_board_sweep.json`](validation100_board_sweep.json),
[`validation100_board_run_summary.csv`](validation100_board_run_summary.csv),
and [`validation100_board_sensors.csv`](validation100_board_sensors.csv).

For the same 100 validation samples offline, fake-QAT action MAE was
`0.12778547` and exported exact-INT8 MAE was `0.12800875` (delta
`+0.00022328`); gripper sign accuracy changed from `93.0973%` to `92.9204%`
(`-0.1770 pp`). Source exact-INT8 versus exported pack parity was exact
(`0.0` max error). These are offline action metrics, not closed-loop success
rates, and the board result above confirms that PL execution matches the
exported exact-INT8 representation.

## Frequency, latency, power, and temperature

The live device-tree clock report on `.120` showed:

```text
pl0_ref  ... 199998000 Hz ... amba_pl:turbovla_fclk0 ... Y
```

The board runtime at commit `49d10eb` measures a monotonic interval around
`executor.run()`, from PS cache/register submission through the observed PL
`done` bit and output invalidation. Twenty runs of the formal replay vector
reported:

```text
LATENCY_SAMPLES count=20 min_us=77085 max_us=77229 mean_us=77162 throughput_hz=12.960
```

Thus the current complete PS/PL inference path sustains about `12.96
inferences/s` (`77.162 ms` per inference), with a measured range of
`12.949..12.973 Hz`. This is end-to-end runtime latency, not pure HLS kernel
latency: it includes cache maintenance, AXI-Lite submission, MMIO polling, and
output invalidation.

The HLS report predicts a maximum of `3,817,800 cycles`, which at the live
`199.998 MHz` clock is `19.089 ms` or `52.386 Hz` before PS/runtime overhead.
The observed end-to-end interval is therefore about `4.04x` that idealized
kernel estimate; this gap is recorded rather than silently presented as PL
compute latency.

Before the full validation sweep, a same-fixture 100-inference load run was
used only as an initial sensor sanity check and reported approximately:

- INA260 board/SOM power: `3.71..4.11 W`;
- PL temperature (`ams/temp3_input`): `26.42..28.61 C`;
- PL internal voltage (`VCC_PSBATT`): about `720 mV`.

These are live board sensor readings and are separate from the Vivado
post-route estimated on-chip power of `3.259 W`.

The board is therefore `action_parity=passed` for this vector. This is a
single-vector parity gate, not a replacement for the existing long-duration
stability evidence from T013.

The `.119` build host remains without XRT development headers. It is only a
software build host; do not copy the board's aarch64 XRT libraries to its
x86_64 filesystem. Use the matching x86_64 Ubuntu 22.04 XRT 2025.1 package or
build XRT from the matching source tag when host-side compilation is needed.
