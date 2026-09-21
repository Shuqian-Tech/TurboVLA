#!/usr/bin/env python3
"""Build and run the host/replay PS runtime model."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runtime"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="turbovla-runtime-csim-") as directory:
        executable = Path(directory) / "tb_runtime"
        subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(SOURCE / "src" / "turbovla_runtime.cpp"),
                str(SOURCE / "src" / "tb_runtime.cpp"),
                "-I",
                str(SOURCE / "include"),
                "-o",
                str(executable),
            ],
            check=True,
        )
        subprocess.run([str(executable)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

