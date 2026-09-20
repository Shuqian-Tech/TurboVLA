# TurboVLA-Lite KR260 software-only timing target: 200 MHz PL clock.
# The Zynq PS generates the PL clock internally; there is no top-level
# ``pl_clk0`` port on the generated wrapper.  ``clk_pl_0`` is emitted by the
# PS clocking XDC and is present when this constraint file is applied.
set_clock_uncertainty -setup 0.200 [get_clocks -quiet clk_pl_0]
