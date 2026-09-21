#!/usr/bin/env python3
"""Build a KR260 fpgautil package from an accepted TurboVLA XSA."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

CONTROL_RANGE_BYTES = 0x10000
PL0_CLOCK_ID = 71
PL0_CLOCK_HZ = 200_000_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_member(archive: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"XSA must contain exactly one {suffix} file, found {matches}")
    return matches[0]


def control_base(hwh: bytes) -> int:
    root = ET.fromstring(hwh)
    matches = [
        node
        for node in root.iter("MEMRANGE")
        if node.get("INSTANCE") == "inference"
        and node.get("SLAVEBUSINTERFACE") == "s_axi_control"
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one inference/s_axi_control range, found {len(matches)}")
    value = matches[0].get("BASEVALUE")
    if value is None:
        raise RuntimeError("inference control range has no BASEVALUE")
    return int(value, 0)


def archive_control_base(archive: zipfile.ZipFile) -> int:
    matches: list[int] = []
    for name in archive.namelist():
        if not name.endswith(".hwh"):
            continue
        try:
            matches.append(control_base(archive.read(name)))
        except RuntimeError:
            continue
    if len(matches) != 1:
        raise RuntimeError(f"expected one XSA HWH with inference control, found {len(matches)}")
    return matches[0]


def overlay_source(bitstream_name: str, base: int) -> str:
    base_hi = base >> 32
    base_lo = base & 0xFFFF_FFFF
    return f"""/dts-v1/;
/plugin/;

/ {{
    fragment@0 {{
        target = <&fpga_full>;
        __overlay__ {{
            firmware-name = "{bitstream_name}";
            resets = <&zynqmp_reset 116>, <&zynqmp_reset 117>,
                     <&zynqmp_reset 118>, <&zynqmp_reset 119>;
        }};
    }};

    fragment@1 {{
        target = <&amba_pl>;
        __overlay__ {{
            #address-cells = <2>;
            #size-cells = <2>;

            turbovla_fclk0 {{
                compatible = "xlnx,fclk";
                clocks = <&zynqmp_clk {PL0_CLOCK_ID}>;
                assigned-clocks = <&zynqmp_clk {PL0_CLOCK_ID}>;
                assigned-clock-rates = <{PL0_CLOCK_HZ}>;
            }};

            turbovla_lite_e2e@{base:x} {{
                compatible = "generic-uio";
                linux,uio-name = "turbovla-lite-e2e";
                reg = <0x{base_hi:x} 0x{base_lo:08x} 0x0 0x{CONTROL_RANGE_BYTES:x}>;
                clocks = <&zynqmp_clk {PL0_CLOCK_ID}>;
                clock-names = "ap_clk";
                assigned-clocks = <&zynqmp_clk {PL0_CLOCK_ID}>;
                assigned-clock-rates = <{PL0_CLOCK_HZ}>;
            }};

            zyxclmm_drm {{
                compatible = "xlnx,zocl";
                status = "okay";
            }};
        }};
    }};
}};
"""


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required tool not found: {name}")
    return path


def package(xsa_path: Path, output_dir: Path) -> dict[str, object]:
    bootgen = require_tool("bootgen")
    dtc = require_tool("dtc")
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(xsa_path) as archive:
        bit_member = archive_member(archive, ".bit")
        bit_path = output_dir / "turbovla_kr260.bit"
        bit_path.write_bytes(archive.read(bit_member))
        base = archive_control_base(archive)

    with tempfile.TemporaryDirectory(prefix="turbovla-kr260-package-") as temp_dir:
        bif_path = Path(temp_dir) / "turbovla_kr260.bif"
        bif_path.write_text(
            f"all:\n{{\n  [destination_device=pl] {bit_path}\n}}\n",
            encoding="ascii",
        )
        subprocess.run(
            [bootgen, "-arch", "zynqmp", "-image", str(bif_path), "-w", "-process_bitstream", "bin"],
            check=True,
        )

    bit_bin_path = bit_path.with_suffix(".bit.bin")
    if not bit_bin_path.is_file():
        raise RuntimeError(f"bootgen did not create {bit_bin_path}")

    dts_path = output_dir / "turbovla_kr260.dts"
    dtbo_path = output_dir / "turbovla_kr260.dtbo"
    dts_path.write_text(overlay_source(bit_bin_path.name, base), encoding="ascii")
    subprocess.run(
        [dtc, "-@", "-I", "dts", "-O", "dtb", "-o", str(dtbo_path), str(dts_path)],
        check=True,
    )
    shell_path = output_dir / "shell.json"
    shell_path.write_text(json.dumps({"shell_type": "XRT_FLAT", "num_slots": "1"}, indent=2) + "\n")

    artifacts = [bit_path, bit_bin_path, dtbo_path, dts_path, shell_path]
    manifest: dict[str, object] = {
        "platform": "kr260-k26",
        "source_xsa": str(xsa_path.resolve()),
        "control_base": f"0x{base:x}",
        "control_range_bytes": CONTROL_RANGE_BYTES,
        "pl0_clock_hz": PL0_CLOCK_HZ,
        "artifacts": {path.name: sha256(path) for path in artifacts},
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("xsa", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.xsa, args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
