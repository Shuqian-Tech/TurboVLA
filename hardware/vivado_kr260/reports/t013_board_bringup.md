# T013 KR260 Board Bring-up

- Test date: 2026-09-21 06:17 UTC
- Target: `amd-edf@192.168.68.123`
- Board kernel: `6.18.10-xilinx-g4f7afe14f724`
- Vivado artifact source: commit `64acaa93803c56168a78063dcf2f2b52fd5d59ff`
- Initial runtime source: commit `aad4f42`
- Clock-overlay fix: commit `ee22fc1`
- Final runtime and stability source: commit `dc31221`

## Artifacts

- XSA SHA256: `1bd062dff74a7a5127c56bf6d45d729483eb768861b1a69c72d7be204831d81e`
- Vivado bit SHA256: `771acd4805977326bd45970e2fcc4e8d029a76eae85d161061b92938f050be5b`
- Board bit.bin SHA256: `55c2c5c5c03c43346e0df6918ce257a4cdc813789dcf0b96df87542262cc013c`
- Board DTBO SHA256: `a4fe03cd15e4078a3c4d1eeb4b1d6b5a7e89af8e0e2eefbc57e0bf844bad1bc9`
- Control map: `0xa0000000`, 64 KiB

The FPGA manager reported `operating`, the `full` overlay reported `applied`,
and `/dev/uio4` was exposed as `turbovla-lite-e2e` with `root:video 0660`.

## AXI-Lite Lockup Root Cause

The first runtime attempt on the original overlay made the board unreachable.
Before any later runtime start, JTAG reads of `0xa0000000` returned an AXI AP
transaction error. The PL0 common-clock state then showed:

```text
pl0_ref enable_count=0 rate=199998000 hardware_enable=N
CRL_APB_PL0_REF_CTRL (0xFF5E00C0)=0x00010500
```

`CLKACT` bit 24 was clear. The original DTBO attached a clock phandle to the
`generic-uio` node, but that driver did not prepare or enable the clock.
Temporarily setting `CLKACT` changed the register to `0x01010500`; JTAG could
then read `0xa0000000` and returned the idle HLS control value `0x00000004`.

The persistent fix adds an `xlnx,fclk` consumer to the generated overlay. To
prove the fix independently of the temporary register write, the old overlay
was removed, `CLKACT` was explicitly cleared, and the new overlay was loaded.
The live clock state became:

```text
pl0_ref enable_count=1 rate=199998000 hardware_enable=Y
consumer=amba_pl:turbovla_fclk0
```

JTAG again read the complete control window successfully.

## Runtime Results

The non-starting probe passed:

```text
KR260 board stage=uio_ready control=0x4
KR260 board stage=xrt_ready arena_address=0x4b1c0000 arena_bytes=200320
KR260 board stage=model_ready
KR260 board probe passed; PL start not issued
```

The full PL inference then completed and matched all 84 action values:

```text
KR260 board stage=start_pl
KR260 board stage=pl_return result=0
KR260 action parity max_abs_error=1.86265e-09 mean_abs_error=4.14556e-10
```

No CPU inference fallback was used. The PS allocated and synchronized the XRT
buffer, programmed the AXI-Lite control registers, and read back PL output.
The board runtime was then rebuilt from exact commit `dc31221`; its probe-only
and full-inference modes passed again with the same 84-value parity metrics.

## Thirty-Minute Stability

The board runtime from exact commit `dc31221` ran continuously from
`2026-09-21T06:35:56+00:00` through `2026-09-21T07:05:56+00:00`. Every
iteration had a 10-second outer timeout and compared all 84 action values with
the checked-in golden vector.

```text
KR260_STABILITY_PASS count=17019 end=2026-09-21T07:05:56+00:00
KR260 board stage=pl_return result=0
KR260 action parity max_abs_error=1.86265e-09 mean_abs_error=4.14556e-10
```

No timeout, PL error, non-finite value, parity failure, SSH disconnect, or
board reset occurred. After the run, the kernel error/critical `dmesg` query
returned no entries and `/proc/uptime` exceeded 3927 seconds. Sensor samples
remained stable:

| Elapsed | Temp_PL | Board power |
|---|---:|---:|
| Start | 31.5 C | 3.80 W |
| About 10 minutes | 31.1 C | 3.93 W |
| About 20 minutes | 30.9 C | 3.80 W |
| End | 31.8 C | 3.58 W |

At the end of the run, the FPGA manager remained `operating`, the `full`
overlay remained `applied`, and `pl0_ref` remained enabled at 199.998 MHz with
`enable_count=1` and consumer `amba_pl:turbovla_fclk0`.

## Remaining Notes

- Exact-commit HLS RTL co-simulation and the T013 thermo-nuclear review passed;
  see [`t013/README.md`](t013/README.md).
- PR #2 review and merge remain before the task can be marked `done`.
- `zocl` logs missing IRQ/CMA reserved-memory warnings during overlay load, but
  device initialization, BO allocation, synchronization, and inference passed.
