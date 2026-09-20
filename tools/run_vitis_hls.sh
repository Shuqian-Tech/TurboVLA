#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <hls-tcl-script>" >&2
  exit 2
fi

script_path=$(realpath "$1")
vitis_root=${TURBOVLA_VITIS_ROOT:-${XILINX_HLS:-${XILINX_VITIS:-}}}
if [[ -z "$vitis_root" ]]; then
  for candidate in \
    /home/frank/AMDDesignTools/2025.1/2025.1/Vitis \
    /tools/Xilinx/Vitis/2025.1 \
    /opt/Xilinx/Vitis/2025.1; do
    if [[ -x "$candidate/bin/unwrapped/lnx64.o/vitis_hls" ]]; then
      vitis_root=$candidate
      break
    fi
  done
fi

hls_binary="$vitis_root/bin/unwrapped/lnx64.o/vitis_hls"
loader="$vitis_root/bin/loader"
vitis_runner="$vitis_root/bin/vitis-run"
if [[ ! -x "$vitis_runner" && (! -x "$hls_binary" || ! -x "$loader") ]]; then
  echo "Vitis HLS 2025.1 installation not found; set TURBOVLA_VITIS_ROOT" >&2
  exit 1
fi

vivado_root=${TURBOVLA_VIVADO_ROOT:-$(dirname "$vitis_root")/Vivado}
locale_root=${TURBOVLA_LOCALE_ROOT:-${TMPDIR:-/tmp}/turbovla-locale}
if [[ ! -d "$locale_root/en_US.UTF-8" ]]; then
  mkdir -p "$locale_root"
  localedef -i en_US -f UTF-8 "$locale_root/en_US.UTF-8"
fi

export LOCPATH="$locale_root"
export RDI_BINROOT="$vitis_root/bin"
export RDI_APPROOT="$vitis_root"
export RDI_BASEROOT="$(dirname "$vitis_root")"
export RDI_INSTALLROOT="$(dirname "$(dirname "$vitis_root")")"
export RDI_INSTALLVER="$(basename "$RDI_BASEROOT")"
export RDI_INSTALLVERSION="$RDI_INSTALLVER"
export RDI_DATADIR="$vitis_root/data"
export XILINX_VITIS="$vitis_root"
export XILINX_HLS="$vitis_root"
export XILINX_VIVADO="$vivado_root"
export TCL_LIBRARY="$vivado_root/../tps/tcl/tcl8.6"
export PYTHONHOME="$vitis_root/tps/lnx64/python-3.13.0"
export LD_LIBRARY_PATH="$($vitis_root/bin/ldlibpath.sh "$vitis_root/lib/lnx64.o"):$vitis_root/lib/lnx64.o:$PYTHONHOME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# Vitis 2025.1's new HLS runner fixes the legacy vitis_hls co-sim
# instrumentation path (COSIM 212-5). Keep the legacy entry point only as a
# fallback for older installations that do not ship vitis-run.
if [[ -x "$vitis_runner" ]]; then
  exec "$vitis_runner" --mode hls --tcl "$script_path"
fi

cd "$vitis_root/bin"
exec "$loader" -exec vitis_hls -f "$script_path"
