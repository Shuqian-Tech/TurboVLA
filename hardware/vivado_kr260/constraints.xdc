# TurboVLA-Lite KR260 software-only timing target: 200 MHz PL clock.
create_clock -name pl_clk0 -period 5.000 [get_ports pl_clk0]
set_clock_uncertainty -setup 0.200 [get_clocks pl_clk0]
set_clock_uncertainty -hold 0.050 [get_clocks pl_clk0]
