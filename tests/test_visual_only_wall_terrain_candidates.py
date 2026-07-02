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
WALL_SOURCE = REPO_ROOT / "assets" / "visual" / "lol_skin" / "wall_5v5_position_locked_source.png"
WALL_CANDIDATE = REPO_ROOT / "assets" / "visual" / "lol_skin" / "wall_5v5_candidate.png"
WALL_FRONT_SOURCE = REPO_ROOT / "assets" / "visual" / "lol_skin" / "wall_5v5_front_position_locked_source.png"
WALL_FRONT_CANDIDATE = REPO_ROOT / "assets" / "visual" / "lol_skin" / "wall_5v5_front_candidate.png"
WALL_TEXTURE_REFERENCE = REPO_ROOT / "assets" / "visual" / "lol_skin" / "wall_terrain_texture_reference.png"
RUNTIME_WALL = MOD_ROOT / "aseprite_resources" / "ingame" / "5v5" / "wall_5v5.png"
RUNTIME_WALL_FRONT = MOD_ROOT / "aseprite_resources" / "ingame" / "5v5" / "wall_5v5_front.png"
OVERRIDE_INFO = MOD_ROOT / "mod.override_info"


class VisualOnlyWallTerrainCandidateTests(unittest.TestCase):
    def test_wall_texture_reference_is_not_runtime_layout_source(self) -> None:
        self.assertTrue(WALL_TEXTURE_REFERENCE.is_file())
        with Image.open(WALL_TEXTURE_REFERENCE) as image:
            self.assertEqual((1254, 1254), image.size)
            self.assertIn(image.mode, {"RGB", "RGBA"})

    def test_position_locked_wall_sources_exist(self) -> None:
        self.assertEqual(WALL_SOURCE, build_runtime_spike_assets.DEFAULT_WALL_SOURCE)
        self.assertEqual(WALL_FRONT_SOURCE, build_runtime_spike_assets.DEFAULT_WALL_FRONT_SOURCE)
        expected_nonzero = {
            WALL_SOURCE: 291_274,
            WALL_FRONT_SOURCE: 56_022,
        }
        for source in (WALL_SOURCE, WALL_FRONT_SOURCE):
            self.assertTrue(source.is_file())
            with Image.open(source) as image:
                self.assertEqual((1280, 1280), image.size)
                self.assertEqual("RGBA", image.mode)
                self.assertEqual(0, image.getchannel("A").getextrema()[0])
                self.assertEqual(
                    expected_nonzero[source],
                    sum(1 for value in image.getchannel("A").getdata() if value > 0),
                )

    def test_wall_candidates_exist_and_match_native_dimensions(self) -> None:
        self.assertEqual(WALL_CANDIDATE, build_runtime_spike_assets.DEFAULT_WALL_CANDIDATE)
        self.assertEqual(WALL_FRONT_CANDIDATE, build_runtime_spike_assets.DEFAULT_WALL_FRONT_CANDIDATE)
        for candidate in (WALL_CANDIDATE, WALL_FRONT_CANDIDATE):
            self.assertTrue(candidate.is_file())
            with Image.open(candidate) as image:
                self.assertEqual((1280, 1280), image.size)
                self.assertEqual("RGBA", image.mode)
                alpha_extrema = image.getchannel("A").getextrema()
                self.assertEqual(0, alpha_extrema[0])
                self.assertGreater(alpha_extrema[1], 100)

    def test_candidates_preserve_position_locked_source_alpha_masks(self) -> None:
        for source, candidate in ((WALL_SOURCE, WALL_CANDIDATE), (WALL_FRONT_SOURCE, WALL_FRONT_CANDIDATE)):
            source_alpha = list(Image.open(source).convert("RGBA").getchannel("A").getdata())
            candidate_alpha = list(Image.open(candidate).convert("RGBA").getchannel("A").getdata())
            self.assertEqual(
                0,
                sum((source_value > 0) != (candidate_value > 0) for source_value, candidate_value in zip(source_alpha, candidate_alpha)),
            )

    def test_builder_can_generate_wall_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wall_output = root / "wall_5v5_candidate.png"
            front_output = root / "wall_5v5_front_candidate.png"

            wall_output.write_bytes(
                build_runtime_spike_assets.png_bytes(build_runtime_spike_assets.build_wall_candidate(96))
            )
            front_output.write_bytes(
                build_runtime_spike_assets.png_bytes(build_runtime_spike_assets.build_wall_front_candidate(96))
            )

            for output in (wall_output, front_output):
                with Image.open(output) as image:
                    self.assertEqual((96, 96), image.size)
                    self.assertEqual("RGBA", image.mode)
                    self.assertEqual(0, image.getchannel("A").getextrema()[0])

        self.assertTrue(RUNTIME_WALL.exists())
        self.assertTrue(RUNTIME_WALL_FRONT.exists())

    def test_committed_candidates_match_deterministic_builder(self) -> None:
        self.assertEqual(
            WALL_CANDIDATE.read_bytes(),
            build_runtime_spike_assets.png_bytes(build_runtime_spike_assets.build_wall_candidate(1280)),
        )
        self.assertEqual(
            WALL_FRONT_CANDIDATE.read_bytes(),
            build_runtime_spike_assets.png_bytes(build_runtime_spike_assets.build_wall_front_candidate(1280)),
        )

    def test_runtime_wall_files_match_committed_candidates(self) -> None:
        self.assertTrue(RUNTIME_WALL.exists())
        self.assertTrue(RUNTIME_WALL_FRONT.exists())
        self.assertEqual(WALL_CANDIDATE.read_bytes(), RUNTIME_WALL.read_bytes())
        self.assertEqual(WALL_FRONT_CANDIDATE.read_bytes(), RUNTIME_WALL_FRONT.read_bytes())

    def test_runtime_package_enables_wall_but_still_excludes_gameplay_data(self) -> None:
        self.assertTrue(RUNTIME_WALL.exists())
        self.assertTrue(RUNTIME_WALL_FRONT.exists())
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
