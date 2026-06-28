from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools import correlate_map_setting_masks_with_visuals as q2n
from tools import map_setting_round_trip
from test_map_setting_round_trip import pack_chunked_binary_matrix, pack_packed4
from test_q2l_no15_singleton_components import synthetic_singleton_map_setting


def synthetic_asymmetric_singleton_map_setting(logical_size: int = 4) -> bytes:
    matrix_size = logical_size * logical_size
    singleton_nodes = {6, 12, 13, 14}
    large_nodes = set(range(matrix_size)) - singleton_nodes
    chunked: list[int] = []
    packed0: list[int] = []
    for source in range(matrix_size):
        for target in range(matrix_size):
            source_singleton = source in singleton_nodes
            target_singleton = target in singleton_nodes
            if source == target:
                chunked.append(0)
                packed0.append(15)
            elif source in large_nodes and target in large_nodes:
                chunked.append(1)
                packed0.append(0)
            elif source_singleton != target_singleton:
                chunked.append(1)
                packed0.append(15)
            else:
                chunked.append(0)
                packed0.append(15)
    packed1: list[int] = []
    for node in range(matrix_size):
        if node in singleton_nodes:
            packed1.extend([8] * logical_size)
        else:
            packed1.extend([node % 4] * logical_size)
    return pack_chunked_binary_matrix(chunked, logical_size=logical_size) + pack_packed4(packed0) + pack_packed4(packed1)


class Q2nMapSettingMaskVisualCorrelationTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_asymmetric_singleton_map_setting())
        return source

    def write_wall_image(self, root: Path) -> Path:
        path = root / "assets" / "wall_5v5.png"
        path.parent.mkdir(parents=True)
        image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        pixels = image.load()
        # This is the rotate180 projection of singleton nodes {6, 12, 13, 14}.
        for cell_x, cell_y in ((1, 1), (1, 0), (2, 0), (3, 0)):
            for y in range(cell_y * 10, cell_y * 10 + 10):
                for x in range(cell_x * 10, cell_x * 10 + 10):
                    pixels[x, y] = (30, 30, 30, 255)
        image.save(path)
        return path

    def test_analysis_writes_json_png_only_and_detects_transform_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            wall = self.write_wall_image(root)
            output_dir = root / "evidence"

            manifest = q2n.correlate_map_setting_masks_with_visuals(
                map_setting=source,
                output_dir=output_dir,
                asset_sources={"wall_5v5": wall},
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            expected_files = [
                "structural_masks_manifest.json",
                "profile_0001_mask_30x30.png",
                "no15_large_component_mask_30x30.png",
                "code15_bridge_endpoint_heatmap_30x30.png",
                "packed4_0_direction_confidence_mask_30x30.png",
                "visual_resource_manifest.json",
                "transform_score_summary.json",
                "q2n_visual_correlation_interpretation.json",
                "overlay_profile0001_rotate180.png",
                "overlay_large_component_rotate180.png",
                "overlay_bridge_heatmap_rotate180.png",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2n.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertEqual("single_transform_candidate", manifest["visual_correlation_result"])
            self.assertEqual("rotate180", manifest["candidate_transform"])
            self.assertEqual("candidate_not_proven", manifest["node_world_transform"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            wall = self.write_wall_image(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2n"

            with self.assertRaises(SystemExit) as raised:
                q2n.correlate_map_setting_masks_with_visuals(
                    map_setting=source,
                    output_dir=output_dir,
                    asset_sources={"wall_5v5": wall},
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_asymmetric_singleton_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            wall = self.write_wall_image(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "structural_masks_manifest.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2n.correlate_map_setting_masks_with_visuals(
                    map_setting=source,
                    output_dir=output_dir,
                    asset_sources={"wall_5v5": wall},
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite", str(raised.exception))
            self.assertEqual(before, source.read_bytes())

    def test_rejects_visual_asset_inside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            with self.assertRaises(SystemExit) as raised:
                q2n.correlate_map_setting_masks_with_visuals(
                    map_setting=source,
                    output_dir=output_dir,
                    asset_sources={"wall_5v5": Path(__file__)},
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("repository-internal asset", str(raised.exception))
            self.assertEqual(synthetic_asymmetric_singleton_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())


if __name__ == "__main__":
    unittest.main()
