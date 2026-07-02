from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools import build_runtime_spike_assets
from tools import summarize_spike_status


REPO_ROOT = Path(__file__).resolve().parents[1]
MOD_ROOT = REPO_ROOT / "mods" / "tfm2_lol_map_spike"
IMAGEGEN_SOURCE = REPO_ROOT / "assets" / "visual" / "lol_skin" / "background_5v5_imagegen_source.png"
BACKGROUND = MOD_ROOT / "aseprite_resources" / "ingame" / "5v5" / "background_5v5.png"
RUNTIME_WALL = MOD_ROOT / "aseprite_resources" / "ingame" / "5v5" / "wall_5v5.png"
RUNTIME_WALL_FRONT = MOD_ROOT / "aseprite_resources" / "ingame" / "5v5" / "wall_5v5_front.png"
OVERRIDE_INFO = MOD_ROOT / "mod.override_info"


class VisualOnlySkinPackageTests(unittest.TestCase):
    def test_imagegen_source_asset_exists(self) -> None:
        self.assertEqual(IMAGEGEN_SOURCE, build_runtime_spike_assets.DEFAULT_SOURCE)
        self.assertTrue(IMAGEGEN_SOURCE.is_file())
        with Image.open(IMAGEGEN_SOURCE) as image:
            self.assertEqual((1254, 1254), image.size)
            self.assertEqual("RGB", image.mode)

    def test_background_skin_exists_and_is_native_size(self) -> None:
        self.assertTrue(BACKGROUND.is_file())
        with Image.open(BACKGROUND) as image:
            self.assertEqual((1280, 1280), image.size)
            self.assertEqual("RGBA", image.mode)
            sample_points = [
                (96, 96),
                (220, 1070),
                (640, 640),
                (1060, 220),
                (1090, 1090),
            ]
            colors = {image.getpixel(point) for point in sample_points}
            self.assertGreater(len(colors), 3)

    def test_builder_outputs_visual_skin_not_flat_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "background_5v5.png"

            image = build_runtime_spike_assets.build_lol_like_background(256)
            image.save(output)

            with Image.open(output) as generated:
                self.assertEqual((256, 256), generated.size)
                colors = {
                    generated.getpixel(point)
                    for point in [(20, 20), (48, 220), (128, 128), (220, 48), (220, 220)]
                }
            self.assertGreater(len(colors), 3)

    def test_override_package_is_visual_only_and_excludes_gameplay_data(self) -> None:
        self.assertTrue(BACKGROUND.is_file())
        self.assertTrue(RUNTIME_WALL.is_file())
        self.assertTrue(RUNTIME_WALL_FRONT.is_file())
        self.assertFalse((MOD_ROOT / "setting" / "map_setting.map_setting").exists())

        table = json.loads(OVERRIDE_INFO.read_text(encoding="utf-8"))
        self.assertEqual(
            {
                "asset/base/aseprite_resources/ingame/5v5/background_5v5",
                "asset/base/aseprite_resources/ingame/5v5/wall_5v5",
                "asset/base/aseprite_resources/ingame/5v5/wall_5v5_front",
            },
            set(table),
        )
        serialized = json.dumps(table, sort_keys=True)
        self.assertNotIn("asset/base/setting/map_setting", serialized)
        self.assertNotIn("setting/map_setting.map_setting", serialized)
        self.assertNotIn("minimap_5v5_bg", serialized)

    def test_route_status_still_blocks_gameplay_mutation(self) -> None:
        matrix = summarize_spike_status.build_status_matrix()
        self.assertFalse(matrix["runtime_mutation_allowed"])
        self.assertFalse(matrix["packed4_mutation_allowed"])
        self.assertFalse(matrix["third_chunked_binary_runtime_probe_allowed"])
        self.assertFalse(matrix["map_editing_allowed"])
        self.assertEqual("route_a_visual_only_deliverable", matrix["next_pr_recommendation"]["preferred"])


if __name__ == "__main__":
    unittest.main()
