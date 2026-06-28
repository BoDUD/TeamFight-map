from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import analyze_packed4_1_node_profiles as q2m
from tools import map_setting_round_trip
from test_q2l_no15_singleton_components import synthetic_singleton_map_setting


class Q2mPacked41NodeProfileTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_singleton_map_setting())
        return source

    def test_analysis_writes_json_only_and_detects_singleton_only_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            manifest = q2m.analyze_packed4_1_node_profiles(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            expected_files = [
                "packed4_1_node_profile_catalog.json",
                "packed4_1_profile_spatial_patterns.json",
                "packed4_1_profile_component_correlation.json",
                "packed4_1_profile_bridge_correlation.json",
                "packed4_1_profile_tracked_nodes.json",
                "q2m_packed4_1_profile_interpretation.json",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2m.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertEqual("node_class_descriptor_candidate", manifest["packed4_1_node_major_role"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

            catalog = json.loads((output_dir / "packed4_1_node_profile_catalog.json").read_text(encoding="utf-8"))
            singleton = catalog["singleton_profile_summary"]
            self.assertEqual(1, singleton["singleton_unique_profile_count"])
            self.assertTrue(singleton["singleton_profiles_disjoint_from_large"])
            self.assertEqual([8, 8, 8, 8], singleton["singleton_profile"])

            spatial = json.loads((output_dir / "packed4_1_profile_spatial_patterns.json").read_text(encoding="utf-8"))
            patterns = {record["profile_id"]: record for record in spatial["profile_spatial_patterns"]}
            singleton_record = patterns[singleton["singleton_profile_id"]]
            self.assertEqual("matches_no15_singleton_band", singleton_record["spatial_pattern"])

            interpretation = json.loads(
                (output_dir / "q2m_packed4_1_profile_interpretation.json").read_text(encoding="utf-8")
            )
            self.assertEqual("node_class_descriptor_candidate", interpretation["packed4_1_node_major_role"])
            self.assertFalse(interpretation["runtime_mutation_allowed"])
            self.assertFalse(interpretation["packed4_mutation_allowed"])
            self.assertFalse(interpretation["map_editing_allowed"])

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2m"

            with self.assertRaises(SystemExit) as raised:
                q2m.analyze_packed4_1_node_profiles(
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
            hardlink = output_dir / "packed4_1_node_profile_catalog.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2m.analyze_packed4_1_node_profiles(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
