#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output=${1:-"$repo_root/build/runtime/turbovla_board"}
mkdir -p "$(dirname "$output")"

g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  "$repo_root/runtime/src/turbovla_runtime.cpp" \
  "$repo_root/runtime/src/turbovla_board.cpp" \
  -I "$repo_root/runtime/include" \
  -lxrt_coreutil \
  -o "$output"

echo "$output"
