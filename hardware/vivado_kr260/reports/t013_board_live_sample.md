# T013 Live KR260 Sample

- Sample date: 2026-09-21 10:55:37-10:56:33 UTC
- Target: `amd-edf@192.168.68.123` (KR260 revB)
- Source/runtime: board runtime built from the T013 bring-up checkout
- Sampling: 12 samples at approximately 5-second intervals while one full PL inference was run per sample
- Inference result: `12/12` successful; the last run reported action max absolute error `1.86265e-09` and mean absolute error `4.14556e-10`
- Raw data: [`t013_board_live_sample.csv`](t013_board_live_sample.csv)

## Observed Ranges

| Signal | Minimum | Maximum | Interpretation |
|---|---:|---:|---|
| `Temp_PL` | 29.003 C | 31.396 C | No thermal rise or runaway in this short load sample |
| `Temp_LPD` | 30.293 C | 32.655 C | Stable PS low-power-domain sensor |
| `Temp_FPD` | 29.764 C | 31.490 C | Stable PS full-power-domain sensor |
| INA260 board power | 3.350 W | 3.440 W | Narrow board-level envelope during repeated inference |
| `VCCINT` | 719 mV | 721 mV | No visible rail excursion |
| `VCCBRAM` | 841 mV | 846 mV | No visible rail excursion |

The FPGA manager stayed `operating`, the TurboVLA overlay stayed `applied`, and
the PL0 control register stayed `0x01010500` (clock active). The overlay carries
a 200 MHz PL0 assignment; the accepted 30-minute board record measured
`199.998 MHz`. This short sample does not replace the 30-minute stability gate
or a long-run thermal limit test.

## Robustness Assessment

This sample supports the claim that the current bitstream/runtime is stable for
repeated deterministic PL inference on the KR260: all transactions completed,
rails stayed within the observed envelope, and the overlay/clock state did not
change. It does not establish worst-case thermal margin, robot workload
success rate, or release timing closure; those remain next-sprint gates.
