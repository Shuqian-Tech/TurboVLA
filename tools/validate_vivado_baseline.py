#!/usr/bin/env python3
"""Validate a KR260 software-only Vivado baseline report manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

LIMITS = {
    "lut_percent": 80.0,
    "ff_percent": 80.0,
    "dsp_percent": 80.0,
    "bram_percent": 80.0,
    "uram_percent": 80.0,
    "total_watts": 15.0,
}


def validate(manifest: dict, allow_not_run: bool = False) -> None:
    if manifest.get("platform") != "kr260-k26":
        raise AssertionError("baseline platform must be kr260-k26")
    if manifest.get("part") != "xck26-sfvc784-2LV-c":
        raise AssertionError("baseline part must be xck26-sfvc784-2LV-c")
    if manifest.get("verification_mode") != "software_only":
        raise AssertionError("baseline must be marked software_only")
    if manifest.get("hardware_bringup") != "not_run":
        raise AssertionError("hardware bring-up must remain not_run for software baseline")
    if allow_not_run:
        return
    for section in ("timing", "utilization", "power", "cdc"):
        if manifest.get(section, {}).get("status") != "passed":
            raise AssertionError(f"{section} report is not passed")
    timing = manifest["timing"]
    if timing["wns_ns"] < 0 or timing["tns_ns"] < 0 or timing["violations"] != 0:
        raise AssertionError("timing report has violations")
    for name, limit in LIMITS.items():
        section = "power" if name == "total_watts" else "utilization"
        value = manifest[section][name]
        if value is None or value >= limit:
            raise AssertionError(f"{name} exceeds baseline limit {limit}")
    if manifest["cdc"]["critical_violations"] != 0:
        raise AssertionError("CDC report has critical violations")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--allow-not-run", action="store_true")
    args = parser.parse_args()
    validate(json.loads(args.manifest.read_text(encoding="utf-8")), allow_not_run=args.allow_not_run)
    print(f"validated KR260 baseline manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

