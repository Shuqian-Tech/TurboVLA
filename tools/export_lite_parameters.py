#!/usr/bin/env python3
"""Export a TurboVLA-Lite checkpoint to an aligned FPGA parameter pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbovla.lite_parameter_pack import export_parameter_pack
from turbovla.lite_reference import load_contract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    manifest = export_parameter_pack(None, args.output_dir, contract=load_contract(), checkpoint=checkpoint)
    print(f"wrote {args.output_dir / 'manifest.json'} with {len(manifest['tensors'])} tensors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
