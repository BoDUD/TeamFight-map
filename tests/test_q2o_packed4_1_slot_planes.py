from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import analyze_packed4_1_slot_planes as q2o
from tools import map_setting_round_trip
from test_map_setting_round_trip import pack_chunked_binary_matrix, pack_packed4


REPO_ROOT = Path(__file__).resolve().parents[1]


def synthetic_slot_plane_map_setting(logical_size: int = 4) -> bytes:
    matrix_size = logical_size * logical_size
    singleton_nodes = {12, 13, 14, 15}
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
            packed1.extend([8, 0, 8, 0])
        else:
            packed1.extend([(node % 4), ((node + 1) % 4), ((node + 2) % 4), ((node + 3) % 4)])
    return pack_chunked_binary_matrix(chunked, logical_size=logical_size) + pack_packed4(packed0) + pack_packed4(packed1)


class Q2oPacked41SlotPlaneTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_slot_plane_map_setting())
        return source

    def test_analysis_writes_json_png_only_and_detects_singleton_slot_signature(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            manifest = q2o.analyze_packed4_1_slot_planes(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            expected_files = [
                "packed4_1_slot_value_histograms.json",
                "packed4_1_slot_spatial_patterns.json",
                "packed4_1_slot_component_correlation.json",
                "packed4_1_slot_pair_correlation.json",
                "profile0001_slot_signature_analysis.json",
                "tracked_node_slot_profiles.json",
                "q2o_packed4_1_slot_interpretation.json",
                "slot_masks/top_slot_value_masks_contact_sheet.png",
                "slot_masks/slot_00_value_8_mask.png",
                "slot_masks/slot_01_value_0_mask.png",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2o.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertEqual("slot_level_node_class_descriptor_candidate", manifest["packed4_1_slot_role"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

            signature = json.loads(
                (output_dir / "profile0001_slot_signature_analysis.json").read_text(encoding="utf-8")
            )
            self.assertEqual([8, 0, 8, 0], signature["singleton_profile"])
            self.assertTrue(signature["alternating_even_8_odd_0"])
            self.assertTrue(signature["full_profile_singleton_exclusive"])

            component = json.loads(
                (output_dir / "packed4_1_slot_component_correlation.json").read_text(encoding="utf-8")
            )
            singleton_only = {
                (record["slot"], record["value"]) for record in component["singleton_only_slot_values"]
            }
            self.assertIn((0, 8), singleton_only)
            self.assertIn((2, 8), singleton_only)

    def test_rejects_output_inside_repository_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = REPO_ROOT / "q2o_repo_output_should_not_exist"

            with self.assertRaises(SystemExit) as raised:
                q2o.analyze_packed4_1_slot_planes(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("repository-internal", str(raised.exception))
            self.assertEqual(synthetic_slot_plane_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2o"

            with self.assertRaises(SystemExit) as raised:
                q2o.analyze_packed4_1_slot_planes(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_slot_plane_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "packed4_1_slot_value_histograms.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2o.analyze_packed4_1_slot_planes(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
