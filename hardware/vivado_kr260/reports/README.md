# KR260 software-only report archive

Vivado `build.tcl` writes utilization, post-route timing, power, and CDC
reports into this directory (or a build-specific copy). Every baseline must
also include a JSON manifest matching `../report_manifest.template.json`.

The manifest is intentionally explicit about `verification_mode:
software_only` and `hardware_bringup: not_run`. A `not_run` manifest is useful
for tracking the environment, but it is not a passing T008 baseline.

T013 hardware evidence is recorded separately in
[`t013_board_bringup.md`](t013_board_bringup.md). It must not be conflated with
the older software-only manifest or the initial read-only board probe.
