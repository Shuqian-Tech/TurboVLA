#!/usr/bin/env python3
"""Build and run the complete image-to-action PL C simulation."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hardware" / "hls" / "e2e"
FIXTURE = ROOT / "tests" / "data" / "lite_hardware_e2e"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE)
    parser.add_argument("--case-index", type=int, choices=range(6))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="turbovla-e2e-csim-") as directory:
        executable = Path(directory) / "tb_e2e"
        subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(SOURCE / "e2e.cpp"),
                str(SOURCE / "tb_e2e.cpp"),
                "-I",
                str(SOURCE),
                "-o",
                str(executable),
            ],
            check=True,
        )
        command = [str(executable), str(args.fixture_dir)]
        if args.case_index is not None:
            command.append(str(args.case_index))
        subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
