set project_dir [file normalize [file join [file dirname [info script]] ../../../build/hls/gemm]]
open_project -reset $project_dir
set_top turbovla_gemm_int8
add_files [file join [file dirname [info script]] gemm.cpp]
add_files -tb [file join [file dirname [info script]] tb_gemm_top.cpp]
open_solution -reset gemm_solution
if {[info exists ::env(TURBOVLA_HLS_SYNTH)] && $::env(TURBOVLA_HLS_SYNTH) eq "1"} {
  set_part xck26-sfvc784-2LV-c
  csynth_design
  export_design -format ip_catalog -output [file normalize [file join $project_dir ip gemm]]
  if {[info exists ::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE)] && $::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE) eq "1"} {
    if {[catch {cosim_design} cosim_error]} {
      puts "WARNING: GEMM co-simulation failed after synthesis: $cosim_error"
    }
  } else {
    cosim_design
  }
  set_top turbovla_conv1x1_int8
  open_solution -reset conv1x1_solution
  set_part xck26-sfvc784-2LV-c
  csynth_design
  export_design -format ip_catalog -output [file normalize [file join $project_dir ip conv1x1]]
  if {[info exists ::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE)] && $::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE) eq "1"} {
    if {[catch {cosim_design} cosim_error]} {
      puts "WARNING: Conv1x1 co-simulation failed after synthesis: $cosim_error"
    }
  } else {
    cosim_design
  }
} else {
  csim_design
}
exit
