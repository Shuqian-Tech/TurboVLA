# T009 KR260 PS Runtime Bring-up

- Date: 2026-09-22
- Target: AMD Kria KR260/K26
- Board: `amd-edf@192.168.68.120`
- Source commit: `281d7d45c42a09eaba902c1da436a063800f7b12`
- Board worktree: `/home/amd-edf/TurboVLA-codex-T009`
- Runtime SHA256: `1e04a7f447783f01a29733544ae723e71a5ddf17006ef1503a93b455f8028e15`
- Active UIO device: `turbovla-lite-e2e`
- FPGA manager after validation: `operating`

The exact pushed commit was fetched from GitHub into a detached board
worktree and built with `tools/build_board_runtime.sh`. The existing TurboVLA
overlay was not reconfigured, and no board or PL reset was issued.

## Validation

Five fixed validation fixtures exercised XRT arena allocation, host-to-device
cache flush, 64-bit arena address programming, AXI-Lite start/poll, PL
inference, device-to-host cache invalidation, header/version/sequence checks,
interrupt state, and all 84 action values.

| Fixture | PL elapsed (ms) | Max absolute error | Mean absolute error | Observed ISR / final GIE/IER/ISR |
| --- | ---: | ---: | ---: | --- |
| 000 | 76.131 | 5.96046e-08 | 1.54167e-08 | 1 / 0/0/0 |
| 025 | 76.020 | 5.96046e-08 | 1.30579e-08 | 1 / 0/0/0 |
| 050 | 76.112 | 5.96046e-08 | 1.16859e-08 | 1 / 0/0/0 |
| 075 | 76.076 | 8.94070e-08 | 1.21515e-08 | 1 / 0/0/0 |
| 099 | 76.094 | 5.96046e-08 | 7.41455e-09 | 1 / 0/0/0 |

Result: `5/5` passed. Mean PL runtime call latency was `76.087 ms`; worst
action max absolute error was `8.94070e-08`. The time includes XRT cache sync,
MMIO programming, polling, and action validation and is not a kernel-only
latency claim.

## Fault And Recovery Coverage

Fault injection remains in the host fake-MMIO test because forcing a real PL
timeout or reset is outside this non-destructive bring-up. The test covers
timeout followed by a successful transaction, invalid arena/model/version,
instruction ID overflow, PL/header errors, unknown return codes, non-finite
actions, cache direction, interrupt enable, and interrupt acknowledge.

The review found that the generated HLS ISR at offset `0x0c` is `Read/TOW`,
not conventional write-one-to-clear. The first implementation wrote all bits,
which could assert a clear status bit. Commit `a711ce5` fixes recovery by
reading the two pending bits and writing back only the asserted mask. The fake
MMIO model uses the same toggle-on-write behavior. Commit `65c57c7` also
captures the asserted completion status, then disables and acknowledges the
interrupt before returning, leaving `GIE/IER/ISR=0/0/0`. This finding is
resolved.

## Commands

```text
python3 tools/run_runtime_csim.py
g++ -std=c++17 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
  runtime/src/turbovla_runtime.cpp runtime/src/tb_runtime.cpp \
  -I runtime/include -o /tmp/turbovla-t009-runtime-sanitize
/tmp/turbovla-t009-runtime-sanitize
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v
python3 tools/validate_mvp_contract.py
python3 tools/validate_kr260_block_manifest.py
```

Local board-runtime compilation was not available because this workstation
does not have XRT development headers. The exact same source compiled and ran
on the KR260, which has the target XRT runtime and headers.
