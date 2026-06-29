from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import analyze_packed4_1_profile_families as q2p
from tools import map_setting_round_trip
from test_map_setting_round_trip import pack_chunked_binary_matrix, pack_packed4


REPO_ROOT = Path(__file__).resolve().parents[1]


def synthetic_profile_family_map_setting(logical_size: int = 4) -> bytes:
    matrix_size = logical_size * logical_size
    singleton_nodes = {12, 13, 14, 15}
    anchor_nodes = {1, 5, 6}
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
        elif node in anchor_nodes:
            packed1.extend([2, 4, 2, 4])
        else:
            packed1.extend([(node % 4), ((node + 1) % 4), ((node + 2) % 4), ((node + 3) % 4)])
    return pack_chunked_binary_matrix(chunked, logical_size=logical_size) + pack_packed4(packed0) + pack_packed4(packed1)


class Q2pPacked41ProfileFamilyTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_profile_family_map_setting())
        return source

    def test_analysis_writes_json_png_only_and_detects_anchor_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            manifest = q2p.analyze_packed4_1_profile_families(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
                hamming_threshold=1,
            )

            expected_files = [
                "packed4_1_profile_family_catalog.json",
                "packed4_1_profile_hamming_clusters.json",
                "packed4_1_profile_family_spatial_patterns.json",
                "packed4_1_profile_family_component_correlation.json",
                "packed4_1_profile_family_anchor_candidates.json",
                "tracked_profile_family_nodes.json",
                "q2p_profile_family_interpretation.json",
                "profile_family_masks/top_profile_family_contact_sheet.png",
                "profile_family_masks/family_0001_mask_30x30.png",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2p.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertEqual("profile_level_node_class_descriptor_candidate", manifest["packed4_1_profile_family_role"])
            self.assertTrue(manifest["asymmetric_anchor_candidates_found"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

            anchors = json.loads(
                (output_dir / "packed4_1_profile_family_anchor_candidates.json").read_text(encoding="utf-8")
            )
            self.assertTrue(anchors["anchor_candidate_profiles"])
            self.assertTrue(anchors["may_use_for_visual_correlation"])
            self.assertFalse(anchors["runtime_mutation_allowed"])
            self.assertFalse(anchors["packed4_mutation_allowed"])
            self.assertFalse(anchors["map_editing_allowed"])

            interpretation = json.loads(
                (output_dir / "q2p_profile_family_interpretation.json").read_text(encoding="utf-8")
            )
            self.assertEqual("unproven", interpretation["node_world_transform"])
            self.assertFalse(interpretation["runtime_mutation_allowed"])
            self.assertFalse(interpretation["packed4_mutation_allowed"])
            self.assertFalse(interpretation["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(interpretation["map_editing_allowed"])

    def test_rejects_output_inside_repository_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = REPO_ROOT / "q2p_repo_output_should_not_exist"

            with self.assertRaises(SystemExit) as raised:
                q2p.analyze_packed4_1_profile_families(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("repository-internal", str(raised.exception))
            self.assertEqual(synthetic_profile_family_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2p"

            with self.assertRaises(SystemExit) as raised:
                q2p.analyze_packed4_1_profile_families(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_profile_family_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "packed4_1_profile_family_catalog.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2p.analyze_packed4_1_profile_families(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
