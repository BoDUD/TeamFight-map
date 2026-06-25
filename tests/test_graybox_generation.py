from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from tools.build_graybox_map import build_svg, build_topology
from tools.validate_map_design import load_layout


class GrayboxGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = load_layout()

    def test_svg_output_is_parseable(self) -> None:
        svg = build_svg(self.layout)
        root = ET.fromstring(svg)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertIn("Morgard", svg)
        self.assertIn("Serpen", svg)

    def test_topology_output_contains_river_bridge(self) -> None:
        topology = build_topology(self.layout)
        self.assertIn("RIVER_TOP", topology)
        self.assertIn("BRIDGE_MID", topology)
        self.assertIn("RIVER_BOTTOM", topology)


if __name__ == "__main__":
    unittest.main()
