set source_dir [file normalize [file dirname [info script]]]
set repo_root [file normalize [file join $source_dir ../../..]]
set project_dir [file normalize [file join $repo_root build/hls/e2e]]
set fixture_dir [file normalize [file join $repo_root tests/data/lite_hardware_e2e]]

open_project -reset $project_dir
set_top turbovla_lite_e2e
add_files [file join $source_dir e2e.cpp]
add_files -tb [file join $source_dir tb_e2e.cpp]
open_solution -reset e2e_solution
set_part xck26-sfvc784-2LV-c
create_clock -period 5.0 -name default

proc turbovla_run_cosim {project_dir fixture_dir} {
  cosim_design -setup -trace_level none -rtl verilog -tool xsim -argv $fixture_dir
  set sim_dir [file normalize [file join $project_dir e2e_solution sim verilog]]
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

csim_design -argv $fixture_dir
if {[info exists ::env(TURBOVLA_HLS_SYNTH)] && $::env(TURBOVLA_HLS_SYNTH) eq "1"} {
  csynth_design
  export_design -format ip_catalog -output [file normalize [file join $project_dir ip turbovla_lite_e2e]]
  if {![info exists ::env(TURBOVLA_HLS_SKIP_COSIM)] || $::env(TURBOVLA_HLS_SKIP_COSIM) ne "1"} {
    turbovla_run_cosim $project_dir $fixture_dir
  }
}
exit
