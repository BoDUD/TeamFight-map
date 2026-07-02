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
MINIMAP_SOURCE = REPO_ROOT / "assets" / "visual" / "lol_skin" / "minimap_5v5_bg_imagegen_source.png"
MINIMAP_CANDIDATE = REPO_ROOT / "assets" / "visual" / "lol_skin" / "minimap_5v5_bg_candidate.png"
BACKGROUND = MOD_ROOT / "aseprite_resources" / "ingame" / "5v5" / "background_5v5.png"
RUNTIME_WALL = MOD_ROOT / "aseprite_resources" / "ingame" / "5v5" / "wall_5v5.png"
RUNTIME_WALL_FRONT = MOD_ROOT / "aseprite_resources" / "ingame" / "5v5" / "wall_5v5_front.png"
RUNTIME_MINIMAP = MOD_ROOT / "aseprite_resources" / "ingame" / "5v5" / "minimap_5v5_bg.png"
OVERRIDE_INFO = MOD_ROOT / "mod.override_info"


class VisualOnlyMinimapCandidateTests(unittest.TestCase):
    def test_minimap_imagegen_source_asset_exists(self) -> None:
        self.assertEqual(MINIMAP_SOURCE, build_runtime_spike_assets.DEFAULT_MINIMAP_SOURCE)
        self.assertTrue(MINIMAP_SOURCE.is_file())
        with Image.open(MINIMAP_SOURCE) as image:
            self.assertEqual((1254, 1254), image.size)
            self.assertEqual("RGB", image.mode)

    def test_minimap_candidate_exists_and_matches_native_dimensions(self) -> None:
        self.assertEqual(MINIMAP_CANDIDATE, build_runtime_spike_assets.DEFAULT_MINIMAP_CANDIDATE)
        self.assertTrue(MINIMAP_CANDIDATE.is_file())
        with Image.open(MINIMAP_CANDIDATE) as image:
            self.assertEqual((320, 320), image.size)
            self.assertEqual("RGBA", image.mode)
            sample_points = [
                (16, 16),
                (48, 272),
                (160, 160),
                (272, 48),
                (304, 304),
            ]
            colors = {image.getpixel(point) for point in sample_points}
            self.assertGreater(len(colors), 3)

    def test_builder_can_generate_candidate_without_touching_runtime_minimap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "minimap_5v5_bg_candidate.png"

            output.write_bytes(
                build_runtime_spike_assets.png_bytes(
                    build_runtime_spike_assets.build_lol_like_minimap_candidate(96)
                )
            )

            with Image.open(output) as generated:
                self.assertEqual((96, 96), generated.size)
                colors = {
                    generated.getpixel(point)
                    for point in [(8, 8), (24, 72), (48, 48), (72, 24), (88, 88)]
                }
            self.assertGreater(len(colors), 3)
        self.assertFalse(RUNTIME_MINIMAP.exists())

    def test_committed_candidate_matches_deterministic_builder(self) -> None:
        rebuilt = build_runtime_spike_assets.png_bytes(
            build_runtime_spike_assets.build_lol_like_minimap_candidate(320)
        )
        self.assertEqual(MINIMAP_CANDIDATE.read_bytes(), rebuilt)

    def test_runtime_package_enables_wall_but_still_excludes_minimap_and_map_setting(self) -> None:
        self.assertTrue(BACKGROUND.is_file())
        self.assertTrue(RUNTIME_WALL.is_file())
        self.assertTrue(RUNTIME_WALL_FRONT.is_file())
        self.assertFalse(RUNTIME_MINIMAP.exists())
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
        self.assertNotIn("minimap_5v5_bg", serialized)
        self.assertNotIn("asset/base/setting/map_setting", serialized)
        self.assertNotIn("setting/map_setting.map_setting", serialized)

    def test_route_status_still_blocks_gameplay_editing(self) -> None:
        matrix = summarize_spike_status.build_status_matrix()
        self.assertFalse(matrix["runtime_mutation_allowed"])
        self.assertFalse(matrix["packed4_mutation_allowed"])
        self.assertFalse(matrix["third_chunked_binary_runtime_probe_allowed"])
        self.assertFalse(matrix["map_editing_allowed"])


if __name__ == "__main__":
    unittest.main()
