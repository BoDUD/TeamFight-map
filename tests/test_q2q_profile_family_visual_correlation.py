from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools import correlate_profile_family_masks_with_visuals as q2q
from tools import map_setting_round_trip
from test_q2p_packed4_1_profile_families import synthetic_profile_family_map_setting


REPO_ROOT = Path(__file__).resolve().parents[1]


def transform_xy(x: int, y: int, size: int, transform: str) -> tuple[int, int]:
    last = size - 1
    if transform == "rotate180":
        return last - x, last - y
    if transform == "identity":
        return x, y
    raise ValueError(transform)


class Q2qProfileFamilyVisualCorrelationTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_profile_family_map_setting())
        return source

    def write_wall_image_for_anchor_family(self, root: Path, transform: str = "rotate180") -> Path:
        path = root / "assets" / "wall_5v5.png"
        path.parent.mkdir(parents=True)
        logical_size = 4
        cell_size = 10
        image = Image.new("RGBA", (logical_size * cell_size, logical_size * cell_size), (0, 0, 0, 0))
        pixels = image.load()
        # In the synthetic source, family_0002 is the asymmetric anchor family with nodes 1, 5, and 6.
        for node in (1, 5, 6):
            x = node % logical_size
            y = node // logical_size
            tx, ty = transform_xy(x, y, logical_size, transform)
            for py in range(ty * cell_size, ty * cell_size + cell_size):
                for px in range(tx * cell_size, tx * cell_size + cell_size):
                    pixels[px, py] = (30, 30, 30, 255)
        image.save(path)
        return path

    def write_blank_background(self, root: Path) -> Path:
        path = root / "assets" / "background_5v5.png"
        path.parent.mkdir(parents=True)
        Image.new("RGBA", (40, 40), (10, 10, 10, 255)).save(path)
        return path

    def test_analysis_writes_json_png_only_and_detects_transform_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            wall = self.write_wall_image_for_anchor_family(root, "rotate180")
            output_dir = root / "evidence"

            manifest = q2q.correlate_profile_family_masks_with_visuals(
                map_setting=source,
                output_dir=output_dir,
                asset_sources={"wall_5v5": wall},
                expected_sha256=map_setting_round_trip.sha256_file(source),
                overlay_family_limit=4,
            )

            expected_files = [
                "profile_family_visual_resource_manifest.json",
                "profile_family_anchor_candidate_manifest.json",
                "profile_family_transform_score_summary.json",
                "per_family_transform_rankings.json",
                "aggregate_transform_vote_summary.json",
                "q2q_profile_family_visual_correlation_interpretation.json",
                "family_mask_overlays/family_0003_rotate180.png",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2q.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertEqual("single_transform_candidate", manifest["q2q_result"])
            self.assertEqual("rotate180", manifest["candidate_transform"])
            self.assertEqual("candidate_not_proven", manifest["node_world_transform"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

            rankings = json.loads((output_dir / "per_family_transform_rankings.json").read_text(encoding="utf-8"))
            family_0003 = next(record for record in rankings["rankings"] if record["family_id"] == "family_0003")
            self.assertEqual("rotate180", family_0003["best_transform"])
            self.assertEqual("single_family_candidate", family_0003["visual_correlation_result"])

    def test_ambiguous_visuals_keep_node_world_transform_unproven(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            background = self.write_blank_background(root)
            output_dir = root / "evidence"

            manifest = q2q.correlate_profile_family_masks_with_visuals(
                map_setting=source,
                output_dir=output_dir,
                asset_sources={"background_5v5": background},
                expected_sha256=map_setting_round_trip.sha256_file(source),
                overlay_family_limit=1,
            )

            self.assertEqual("ambiguous", manifest["q2q_result"])
            self.assertEqual("none", manifest["candidate_transform"])
            self.assertEqual("unproven", manifest["node_world_transform"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

    def test_rejects_output_inside_repository_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            wall = self.write_wall_image_for_anchor_family(root)
            output_dir = REPO_ROOT / "q2q_repo_output_should_not_exist"

            with self.assertRaises(SystemExit) as raised:
                q2q.correlate_profile_family_masks_with_visuals(
                    map_setting=source,
                    output_dir=output_dir,
                    asset_sources={"wall_5v5": wall},
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("repository-internal", str(raised.exception))
            self.assertEqual(synthetic_profile_family_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            wall = self.write_wall_image_for_anchor_family(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2q"

            with self.assertRaises(SystemExit) as raised:
                q2q.correlate_profile_family_masks_with_visuals(
                    map_setting=source,
                    output_dir=output_dir,
                    asset_sources={"wall_5v5": wall},
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_profile_family_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            wall = self.write_wall_image_for_anchor_family(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "profile_family_visual_resource_manifest.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2q.correlate_profile_family_masks_with_visuals(
                    map_setting=source,
                    output_dir=output_dir,
                    asset_sources={"wall_5v5": wall},
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite", str(raised.exception))
            self.assertEqual(before, source.read_bytes())

    def test_rejects_repository_internal_visual_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            with self.assertRaises(SystemExit) as raised:
                q2q.correlate_profile_family_masks_with_visuals(
                    map_setting=source,
                    output_dir=output_dir,
                    asset_sources={"wall_5v5": Path(__file__)},
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("repository-internal asset", str(raised.exception))
            self.assertEqual(synthetic_profile_family_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_visual_asset_under_mods_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            wall = self.write_wall_image_for_anchor_family(root / "game" / "mods" / "some_mod")
            output_dir = root / "evidence"

            with self.assertRaises(SystemExit) as raised:
                q2q.correlate_profile_family_masks_with_visuals(
                    map_setting=source,
                    output_dir=output_dir,
                    asset_sources={"wall_5v5": wall},
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_profile_family_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())


if __name__ == "__main__":
    unittest.main()
