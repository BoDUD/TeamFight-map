from __future__ import annotations

import struct
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGEGEN_MAP = REPO_ROOT / "assets" / "generated" / "tfm2_lol_like_map_imagegen_v1.png"


class GeneratedAssetTests(unittest.TestCase):
    def test_imagegen_map_asset_is_square_png(self) -> None:
        data = IMAGEGEN_MAP.read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual(width, height)
        self.assertGreaterEqual(width, 1024)


if __name__ == "__main__":
    unittest.main()
