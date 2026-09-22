# TurboVLA KR260 PS Runtime

The runtime owns transport and control only. Neural inference remains entirely
inside the `turbovla_lite_e2e` PL IP; there is no PS inference fallback.

## Buffer Ownership

The PS allocates one 64-byte-aligned, physically contiguous 200,320-byte XRT
buffer. The arena layout is defined by
`hardware/contracts/turbovla_lite_contract.json`:

| Region | Owner before start | Owner after start | Cache operation |
| --- | --- | --- | --- |
| header | PS | PL, then PS after completion | flush, then invalidate |
| image | PS | PL read-only | flush |
| state | PS | PL read-only | flush |
| model | PS | PL read-only | flush once after load |
| action | PL | PS after completion | invalidate |

`PlArenaExecutor` writes the frame sequence and fixed-shape inputs, performs
the required cache synchronization, programs the 64-bit arena address through
AXI-Lite, enables the HLS completion interrupt, and starts `ap_ctrl_hs`. It
does not expose the output until the done bit, error fields, contract version,
completion sequence, arena header, and all 84 finite action values pass.

## Timeout And Recovery

A timeout returns `kDmaTimeout` without interpreting the output buffer. Each
new submission first clears stale control and interrupt state. This recovers
from a completed or transiently late transaction without reconstructing the
runtime. `reset_control()` performs the same AXI-Lite cleanup explicitly. It
does not drive the PL reset line; a persistently hung kernel requires the
KR260 platform reset or overlay recovery path.

The board backend maps the HLS AXI-Lite registers through UIO and allocates the
arena through XRT. `tools/run_runtime_csim.py` exercises the same executor with
fake MMIO/cache devices, including cache direction, 64-bit addressing,
interrupt enable/acknowledge, timeout recovery, model/version rejection,
kernel errors, invalid values, and instruction bounds.
