#!/usr/bin/env python3
"""Build and run the fixed-shape fusion/action C simulation."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEMM = ROOT / "hardware" / "hls" / "gemm"
SOURCE = ROOT / "hardware" / "hls" / "fusion_action"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="turbovla-fusion-csim-") as directory:
        executable = Path(directory) / "tb_fusion_action"
        subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(GEMM / "gemm.cpp"),
                str(SOURCE / "fusion_action.cpp"),
                str(SOURCE / "tb_fusion_action.cpp"),
                "-I",
                str(GEMM),
                "-I",
                str(SOURCE),
                "-o",
                str(executable),
            ],
            check=True,
        )
        subprocess.run([str(executable)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

