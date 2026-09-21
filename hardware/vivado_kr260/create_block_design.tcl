# KR260/K26-only TurboVLA-Lite end-to-end block design.
set required_part "xck26-sfvc784-2LV-c"
if {[get_property PART [current_project]] ne $required_part} {
  error "TurboVLA requires KR260/K26 part $required_part"
}

set e2e_defs [get_ipdefs -all -filter {VLNV =~ *:hls:turbovla_lite_e2e:*}]
if {![llength $e2e_defs]} {
  error "T013 turbovla_lite_e2e packaged IP is required before block design creation"
}

create_bd_design "turbovla_kr260"
create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 ps
create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 control_smartconnect
create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 memory_smartconnect
create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 interrupt_concat
create_bd_cell -type ip -vlnv xilinx.com:hls:turbovla_lite_e2e:1.0 inference

set_property -dict [list \
  CONFIG.PSU__USE__M_AXI_GP0 {1} \
  CONFIG.PSU__USE__S_AXI_GP0 {1} \
  CONFIG.PSU__USE__IRQ0 {1} \
  CONFIG.PSU__FPGA_PL0_ENABLE {1} \
  CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {200}] [get_bd_cells ps]
set_property CONFIG.NUM_SI 1 [get_bd_cells control_smartconnect]
set_property CONFIG.NUM_MI 1 [get_bd_cells control_smartconnect]
set_property CONFIG.NUM_SI 1 [get_bd_cells memory_smartconnect]
set_property CONFIG.NUM_MI 1 [get_bd_cells memory_smartconnect]
set_property CONFIG.NUM_PORTS 1 [get_bd_cells interrupt_concat]

connect_bd_net [get_bd_pins ps/pl_clk0] \
  [get_bd_pins control_smartconnect/aclk] \
  [get_bd_pins memory_smartconnect/aclk] \
  [get_bd_pins proc_sys_reset/slowest_sync_clk] \
  [get_bd_pins ps/maxihpm0_fpd_aclk] \
  [get_bd_pins ps/saxihpc0_fpd_aclk] \
  [get_bd_pins inference/ap_clk]
connect_bd_net [get_bd_pins ps/pl_resetn0] \
  [get_bd_pins proc_sys_reset/ext_reset_in] \
  [get_bd_pins memory_smartconnect/aresetn]
connect_bd_net [get_bd_pins proc_sys_reset/peripheral_aresetn] \
  [get_bd_pins control_smartconnect/aresetn] \
  [get_bd_pins inference/ap_rst_n]
connect_bd_net [get_bd_pins inference/interrupt] [get_bd_pins interrupt_concat/In0]
connect_bd_net [get_bd_pins interrupt_concat/dout] [get_bd_pins ps/pl_ps_irq0]

connect_bd_intf_net [get_bd_intf_pins ps/M_AXI_HPM0_FPD] \
  [get_bd_intf_pins control_smartconnect/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins control_smartconnect/M00_AXI] \
  [get_bd_intf_pins inference/s_axi_control]
connect_bd_intf_net [get_bd_intf_pins inference/m_axi_gmem0] \
  [get_bd_intf_pins memory_smartconnect/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins memory_smartconnect/M00_AXI] \
  [get_bd_intf_pins ps/S_AXI_HPC0_FPD]

assign_bd_address
validate_bd_design
save_bd_design
