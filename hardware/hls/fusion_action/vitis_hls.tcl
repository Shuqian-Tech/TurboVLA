set project_dir [file normalize [file join [file dirname [info script]] ../../../build/hls/fusion_action]]
open_project -reset $project_dir
set_top turbovla_gated_fusion_int8
set gemm_source [file normalize [file join [file dirname [info script]] ../gemm/gemm.cpp]]
add_files $gemm_source
add_files [file join [file dirname [info script]] fusion_action.cpp]
add_files -tb [file join [file dirname [info script]] tb_fusion_action.cpp]
open_solution -reset fusion_solution
if {[info exists ::env(TURBOVLA_HLS_SYNTH)] && $::env(TURBOVLA_HLS_SYNTH) eq "1"} {
  set_part xck26-sfvc784-2LV-c
  csynth_design
  export_design -format ip_catalog -output [file normalize [file join $project_dir ip gated_fusion]]
  if {[info exists ::env(TURBOVLA_HLS_SKIP_GATED_COSIM)] && $::env(TURBOVLA_HLS_SKIP_GATED_COSIM) eq "1"} {
    puts "WARNING: gated-fusion co-simulation deferred after RTL setup; synthesis and IP export completed"
  } elseif {[info exists ::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE)] && $::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE) eq "1"} {
    if {[catch {cosim_design -trace_level none -rtl verilog -tool xsim} cosim_error]} {
      puts "WARNING: Gated fusion co-simulation failed after synthesis: $cosim_error"
    }
  } else {
    cosim_design -trace_level none -rtl verilog -tool xsim
  }
  set_top turbovla_action_mlp_int8
  open_solution -reset action_mlp_solution
  set_part xck26-sfvc784-2LV-c
  csynth_design
  export_design -format ip_catalog -output [file normalize [file join $project_dir ip action_mlp]]
  if {[info exists ::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE)] && $::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE) eq "1"} {
    if {[catch {cosim_design -trace_level none -rtl verilog -tool xsim} cosim_error]} {
      puts "WARNING: Action MLP co-simulation failed after synthesis: $cosim_error"
    }
  } else {
    cosim_design -trace_level none -rtl verilog -tool xsim
  }
} else {
  csim_design
}
exit
