set project_dir [file normalize [file join [file dirname [info script]] ../../../build/hls/fusion_action]]
open_project -reset $project_dir
set_top turbovla_gated_fusion_int8
set gemm_source [file normalize [file join [file dirname [info script]] ../gemm/gemm.cpp]]
add_files $gemm_source
add_files [file join [file dirname [info script]] fusion_action.cpp]
add_files -tb [file join [file dirname [info script]] tb_fusion_action.cpp]
open_solution -reset fusion_solution

# Generate the simulator files first so the XSIM launcher can discard the
# waveform database. Keeping WDB disabled is essential for long AXI co-sims.
proc turbovla_run_cosim {project_dir {argv_value ""}} {
  set setup_args [list -setup -trace_level none -rtl verilog -tool xsim]
  if {$argv_value ne ""} {
    lappend setup_args -argv $argv_value
  }
  cosim_design {*}$setup_args

  set sim_dir [file normalize [file join $project_dir fusion_solution sim verilog]]
  set run_script [file join $sim_dir run_xsim.sh]
  set input [open $run_script r]
  set script [read $input]
  close $input
  if {[string first "-wdb /dev/null" $script] < 0} {
    if {![regsub {(/xsim)([[:space:]]+-testplusarg)} $script {\1 -wdb /dev/null\2} script]} {
      error "could not disable XSIM waveform database in $run_script"
    }
    set output [open $run_script w]
    puts -nonewline $output $script
    close $output
  }

  set previous_dir [pwd]
  cd $sim_dir
  set result [catch {source run_sim.tcl} message options]
  cd $previous_dir
  if {$result} {
    return -options $options $message
  }
}

if {[info exists ::env(TURBOVLA_HLS_SYNTH)] && $::env(TURBOVLA_HLS_SYNTH) eq "1"} {
  set_part xck26-sfvc784-2LV-c
  csynth_design
  export_design -format ip_catalog -output [file normalize [file join $project_dir ip gated_fusion]]
  if {[info exists ::env(TURBOVLA_HLS_SKIP_GATED_COSIM)] && $::env(TURBOVLA_HLS_SKIP_GATED_COSIM) eq "1"} {
    puts "WARNING: gated-fusion co-simulation deferred after RTL setup; synthesis and IP export completed"
  } else {
    set gated_cases {0 1}
    if {[info exists ::env(TURBOVLA_HLS_COSIM_CASE)] && $::env(TURBOVLA_HLS_COSIM_CASE) ne ""} {
      set gated_cases [list $::env(TURBOVLA_HLS_COSIM_CASE)]
    }
    foreach gated_case $gated_cases {
      if {[info exists ::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE)] && $::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE) eq "1"} {
        if {[catch {turbovla_run_cosim $project_dir $gated_case} cosim_error]} {
          puts "WARNING: Gated fusion co-simulation case $gated_case failed after synthesis: $cosim_error"
        }
      } else {
        turbovla_run_cosim $project_dir $gated_case
      }
    }
  }
  set_top turbovla_action_mlp_int8
  open_solution -reset action_mlp_solution
  set_part xck26-sfvc784-2LV-c
  csynth_design
  export_design -format ip_catalog -output [file normalize [file join $project_dir ip action_mlp]]
  if {[info exists ::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE)] && $::env(TURBOVLA_HLS_ALLOW_COSIM_FAILURE) eq "1"} {
    if {[catch {turbovla_run_cosim $project_dir} cosim_error]} {
      puts "WARNING: Action MLP co-simulation failed after synthesis: $cosim_error"
    }
  } else {
    turbovla_run_cosim $project_dir
  }
} else {
  csim_design
}
exit
