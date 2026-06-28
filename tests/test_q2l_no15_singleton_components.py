from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import analyze_no15_singleton_components as q2l
from tools import map_setting_round_trip
from test_map_setting_round_trip import pack_chunked_binary_matrix, pack_packed4


def synthetic_singleton_map_setting(logical_size: int = 4) -> bytes:
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
        value = 8 if node in singleton_nodes else node % 4
        packed1.extend([value] * logical_size)
    return pack_chunked_binary_matrix(chunked, logical_size=logical_size) + pack_packed4(packed0) + pack_packed4(packed1)


class Q2lNo15SingletonComponentTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_singleton_map_setting())
        return source

    def test_analysis_writes_json_only_and_classifies_structured_singletons(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            manifest = q2l.analyze_no15_singleton_components(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            expected_files = [
                "no15_singleton_nodes.json",
                "no15_singleton_spatial_pattern.json",
                "code15_singleton_bridge_edges.json",
                "singleton_packed4_1_profiles.json",
                "q2l_singleton_component_interpretation.json",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2l.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertEqual("structured_special_node_set_candidate", manifest["no15_singleton_role"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

            spatial = json.loads((output_dir / "no15_singleton_spatial_pattern.json").read_text(encoding="utf-8"))
            self.assertEqual("border_candidate", spatial["spatial_pattern"])
            self.assertEqual(4, spatial["singleton_count"])

            bridges = json.loads((output_dir / "code15_singleton_bridge_edges.json").read_text(encoding="utf-8"))
            self.assertTrue(bridges["all_singletons_have_code15_bridge"])
            self.assertTrue(bridges["all_singleton_bridge_degrees_symmetric"])
            self.assertEqual(
                96,
                bridges["category_counts"]["large_component_to_singleton"]
                + bridges["category_counts"]["singleton_to_large_component"],
            )

            profiles = json.loads((output_dir / "singleton_packed4_1_profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(
                "strong_unverified",
                profiles["assumptions"]["node_major_900x30"]["singleton_distinguishing_signal"],
            )

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2l"

            with self.assertRaises(SystemExit) as raised:
                q2l.analyze_no15_singleton_components(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_singleton_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "no15_singleton_nodes.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2l.analyze_no15_singleton_components(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
