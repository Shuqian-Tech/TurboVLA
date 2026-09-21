#!/usr/bin/env python3
"""Export the deterministic PL model pack and end-to-end replay vector."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.lite_hardware_pack import export_hardware_fixture


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("tests/data/lite_hardware_e2e"))
    args = parser.parse_args()
    manifest = export_hardware_fixture(args.output_dir)
    print(f"wrote {args.output_dir} model_bytes={manifest['model_bytes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
