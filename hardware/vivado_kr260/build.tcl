# Non-interactive software-only KR260 end-to-end build entry point.
set script_dir [file normalize [file dirname [info script]]]
set project_dir [file normalize [file join $script_dir build]]
set project_name turbovla_kr260
set part xck26-sfvc784-2LV-c

create_project -force $project_name $project_dir -part $part
set_property target_language Verilog [current_project]
set_property ip_repo_paths [list \
  [file normalize [file join $script_dir ../../build/hls/e2e/e2e_solution/impl/ip]]] [current_project]
update_ip_catalog
add_files -fileset constrs_1 [file join $script_dir constraints.xdc]
source [file join $script_dir create_block_design.tcl]
generate_target all [get_files */turbovla_kr260.bd]
make_wrapper -files [get_files */turbovla_kr260.bd] -top
add_files -norecurse [glob -nocomplain $project_dir/$project_name.gen/sources_1/bd/turbovla_kr260/hdl/*.v]
update_compile_order -fileset sources_1
launch_runs synth_1 -jobs 8
wait_on_run synth_1
set_property strategy Performance_ExplorePostRoutePhysOpt [get_runs impl_1]
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1
open_run impl_1
set setup_wns [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
if {$setup_wns < 0.0} {
  puts "Post-route setup WNS is $setup_wns ns; running AggressiveExplore fallback"
  phys_opt_design -directive AggressiveExplore
}
report_utilization -file [file join $project_dir utilization.rpt]
report_timing_summary -file [file join $project_dir timing_summary.rpt]
report_power -file [file join $project_dir power.rpt]
report_cdc -file [file join $project_dir cdc.rpt]
write_bitstream -force [file join $project_dir turbovla_kr260.bit]
write_hw_platform -fixed -include_bit -force -file [file join $project_dir turbovla_kr260.xsa]
