import unittest
import zipfile
from io import BytesIO

from tools.package_kr260 import archive_control_base, control_base, overlay_source


class Kr260PackageTest(unittest.TestCase):
    def test_finds_only_inference_control_range(self) -> None:
        hwh = b"""<SYSTEM><MEMRANGES>
          <MEMRANGE INSTANCE="other" SLAVEBUSINTERFACE="s_axi_control" BASEVALUE="0xa0000000"/>
          <MEMRANGE INSTANCE="inference" SLAVEBUSINTERFACE="s_axi_control" BASEVALUE="0xa0040000"/>
        </MEMRANGES></SYSTEM>"""
        self.assertEqual(control_base(hwh), 0xA0040000)

    def test_rejects_ambiguous_control_ranges(self) -> None:
        hwh = b"""<SYSTEM><MEMRANGES>
          <MEMRANGE INSTANCE="inference" SLAVEBUSINTERFACE="s_axi_control" BASEVALUE="0xa0000000"/>
          <MEMRANGE INSTANCE="inference" SLAVEBUSINTERFACE="s_axi_control" BASEVALUE="0xa0010000"/>
        </MEMRANGES></SYSTEM>"""
        with self.assertRaisesRegex(RuntimeError, "expected one"):
            control_base(hwh)

    def test_selects_top_level_hwh_from_multi_hwh_xsa(self) -> None:
        archive_bytes = BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as archive:
            archive.writestr("smartconnect.hwh", b"<SYSTEM/>")
            archive.writestr(
                "turbovla_kr260.hwh",
                b'<SYSTEM><MEMRANGE INSTANCE="inference" '
                b'SLAVEBUSINTERFACE="s_axi_control" BASEVALUE="0xa0050000"/></SYSTEM>',
            )
        with zipfile.ZipFile(archive_bytes) as archive:
            self.assertEqual(archive_control_base(archive), 0xA0050000)

    def test_overlay_records_runtime_contract(self) -> None:
        source = overlay_source("turbovla_kr260.bit.bin", 0x1A0040000)
        self.assertIn('firmware-name = "turbovla_kr260.bit.bin"', source)
        self.assertIn('linux,uio-name = "turbovla-lite-e2e"', source)
        self.assertIn("reg = <0x1 0xa0040000 0x0 0x10000>", source)
        self.assertIn('compatible = "xlnx,zocl"', source)
        self.assertIn('compatible = "xlnx,fclk"', source)
        self.assertIn("turbovla_fclk0", source)
        self.assertIn("assigned-clock-rates = <200000000>", source)


if __name__ == "__main__":
    unittest.main()
