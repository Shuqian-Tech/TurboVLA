#!/usr/bin/env python3
"""Build and run the portable C simulation for the INT8 GEMM/Conv IP."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hardware" / "hls" / "gemm"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="turbovla-gemm-csim-") as directory:
        executable = Path(directory) / "tb_gemm"
        subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(SOURCE / "gemm.cpp"),
                str(SOURCE / "tb_gemm.cpp"),
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
