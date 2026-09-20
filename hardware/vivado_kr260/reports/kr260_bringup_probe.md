# KR260 Bring-up Probe

- Probe date: 2026-09-20
- Source checkout: `3aa57ff14c33de8d26fafcb5351531b3c89cd0ec`
- Target: `amd-edf@192.168.68.123`
- Probe mode: non-destructive read-only

## Board Reachability

Passwordless SSH succeeded: hostname `amd-edf`, user `amd-edf`, model
`ZynqMP KR260 revB`, kernel `6.18.10-xilinx-g4f7afe14f724`, and `/dev/fpga0`
was present. The FPGA manager reported `state=operating`, but `fpgautil`
requires root, `sudo -n true` failed, and `/dev/fpga0`/`/dev/uio0..3` are
root-owned.

## Active PL Image

Read-only device-tree inspection reported:

```text
/sys/firmware/devicetree/base/amba_pl/firmware-name=kr260_base.bit.bin
/sys/firmware/devicetree/base/fpga-region/firmware-name=k26-starter-kits.bin
/sys/kernel/config/device-tree/overlays/k26-starter-kits_image_1/status=applied
/sys/kernel/config/device-tree/overlays/k26-starter-kits_image_1/path=k26-starter-kits.dtbo
```

The active overlay exposes only four `xilinx_apm` UIO devices. No TurboVLA
GEMM, gated-fusion, action-MLP, AXI-DMA, or scheduler node is present. This is
not a TurboVLA hardware-inference run.

## Local Hardware Manager

The default `hw_server` lacked Vivado cable libraries. A second read-only
server on `TCP:127.0.0.1:3122` loaded Vivado's bundled `libxftdi.so` and
`libdjtg.so.2`; Vivado still returned zero hardware targets. No JTAG device
part was available to verify or program.

## Result

```text
ssh/board probe: passed
active TurboVLA bitstream: not_run
Hardware Manager/JTAG target: not_run (zero targets)
bitstream download: not_run
PL DMA/runtime smoke: not_run
hardware inference: not_run
30-minute stability: not_run
```

No reset, FPGA reconfiguration, bitstream download, or write to board state
was performed.
