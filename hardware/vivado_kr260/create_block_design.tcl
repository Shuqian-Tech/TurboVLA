# KR260/K26-only TurboVLA-Lite block design.
# This script intentionally fails when the packaged T005/T006 IP is absent.

set required_part "xck26-sfvc784-2LV-c"
if {[get_property PART [current_project]] ne $required_part} {
  error "TurboVLA requires KR260/K26 part $required_part"
}

set gemm_defs [get_ipdefs -all -filter {VLNV =~ *:hls:turbovla_gemm_int8:*}]
set fusion_defs [get_ipdefs -all -filter {VLNV =~ *:hls:turbovla_gated_fusion_int8:*}]
if {![llength $gemm_defs] || ![llength $fusion_defs]} {
  error "T005/T006 packaged IP definitions are required before block design creation"
}

create_bd_design "turbovla_kr260"
create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 ps
create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 smartconnect
create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 memory_smartconnect
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:7.1 axi_dma
create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 interrupt_concat
create_bd_cell -type ip -vlnv xilinx.com:hls:turbovla_gemm_int8:1.0 gemm
create_bd_cell -type ip -vlnv xilinx.com:hls:turbovla_gated_fusion_int8:1.0 fusion_action

set_property -dict [list \
  CONFIG.PSU__USE__M_AXI_GP0 {1} \
  CONFIG.PSU__USE__S_AXI_GP0 {1} \
  CONFIG.PSU__USE__S_AXI_ACE {1} \
  CONFIG.PSU__USE__IRQ0 {1} \
  CONFIG.PSU__FPGA_PL0_ENABLE {1}] [get_bd_cells ps]
set_property -dict [list CONFIG.c_include_sg {0} CONFIG.c_include_mm2s {1} CONFIG.c_include_s2mm {0}] [get_bd_cells axi_dma]
set_property CONFIG.NUM_SI 1 [get_bd_cells smartconnect]
set_property CONFIG.NUM_MI 5 [get_bd_cells smartconnect]
set_property CONFIG.NUM_SI 12 [get_bd_cells memory_smartconnect]
set_property CONFIG.NUM_MI 1 [get_bd_cells memory_smartconnect]
set_property CONFIG.NUM_PORTS 1 [get_bd_cells interrupt_concat]

connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins smartconnect/aclk]
connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins memory_smartconnect/aclk]
connect_bd_net [get_bd_pins ps/pl_resetn0] [get_bd_pins memory_smartconnect/aresetn]
connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins ps/maxihpm0_fpd_aclk]
connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins ps/maxihpm0_lpd_aclk]
connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins ps/saxihpc0_fpd_aclk]
connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins ps/sacefpd_aclk]
connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins axi_dma/s_axi_lite_aclk]
connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins axi_dma/m_axi_mm2s_aclk]
connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins proc_sys_reset/slowest_sync_clk]
connect_bd_net [get_bd_pins ps/pl_resetn0] [get_bd_pins proc_sys_reset/ext_reset_in]
connect_bd_net [get_bd_pins ps/pl_clk0] [get_bd_pins gemm/ap_clk] [get_bd_pins fusion_action/ap_clk]
connect_bd_net [get_bd_pins proc_sys_reset/peripheral_aresetn] \
  [get_bd_pins gemm/ap_rst_n] [get_bd_pins fusion_action/ap_rst_n]
connect_bd_net [get_bd_pins axi_dma/mm2s_introut] [get_bd_pins interrupt_concat/In0]
connect_bd_net [get_bd_pins interrupt_concat/dout] [get_bd_pins ps/pl_ps_irq0]

connect_bd_intf_net [get_bd_intf_pins ps/M_AXI_HPM0_FPD] [get_bd_intf_pins smartconnect/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins smartconnect/M00_AXI] [get_bd_intf_pins axi_dma/S_AXI_LITE]
connect_bd_intf_net [get_bd_intf_pins smartconnect/M01_AXI] [get_bd_intf_pins gemm/s_axi_control]
connect_bd_intf_net [get_bd_intf_pins smartconnect/M02_AXI] [get_bd_intf_pins gemm/s_axi_control_r]
connect_bd_intf_net [get_bd_intf_pins smartconnect/M03_AXI] [get_bd_intf_pins fusion_action/s_axi_control]
connect_bd_intf_net [get_bd_intf_pins smartconnect/M04_AXI] [get_bd_intf_pins fusion_action/s_axi_control_r]

set memory_masters [list \
  axi_dma/M_AXI_MM2S \
  gemm/m_axi_gmem0 gemm/m_axi_gmem1 gemm/m_axi_gmem2 gemm/m_axi_gmem3 \
  fusion_action/m_axi_gmem0 fusion_action/m_axi_gmem1 fusion_action/m_axi_gmem2 \
  fusion_action/m_axi_gmem3 fusion_action/m_axi_gmem4 fusion_action/m_axi_gmem5 fusion_action/m_axi_gmem6]
set memory_index 0
foreach master $memory_masters {
  set slave_pin [format "memory_smartconnect/S%02d_AXI" $memory_index]
  connect_bd_intf_net [get_bd_intf_pins $master] [get_bd_intf_pins $slave_pin]
  incr memory_index
}
connect_bd_intf_net [get_bd_intf_pins memory_smartconnect/M00_AXI] [get_bd_intf_pins ps/S_AXI_HPC0_FPD]

assign_bd_address
validate_bd_design
save_bd_design
