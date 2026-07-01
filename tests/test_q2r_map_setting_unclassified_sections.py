from __future__ import annotations

import json
import os
import struct
import tempfile
import unittest
from pathlib import Path

from tools import analyze_map_setting_unclassified_sections as q2r
from tools import map_setting_round_trip
from test_map_setting_round_trip import synthetic_map_setting


REPO_ROOT = Path(__file__).resolve().parents[1]


def write_source(root: Path, residual: bytes = b"") -> Path:
    source = root / "source" / "map_setting"
    source.parent.mkdir(parents=True)
    source.write_bytes(synthetic_map_setting() + residual)
    return source


class Q2rMapSettingUnclassifiedSectionTests(unittest.TestCase):
    def test_analysis_writes_json_png_only_and_detects_900_node_index_candidate(self) -> None:
        residual = b"".join(struct.pack("<H", value) for value in range(900))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = write_source(root, residual)
            output_dir = root / "evidence"

            manifest = q2r.analyze_map_setting_unclassified_sections(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            expected_files = [
                "map_setting_section_inventory.json",
                "map_setting_residual_span_entropy.json",
                "dimensioned_array_candidates.json",
                "coordinate_like_value_candidates.json",
                "cross_layer_index_reference_candidates.json",
                "tracked_node_unclassified_context.json",
                "q2r_unclassified_section_interpretation.json",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2r.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

            dimensions = json.loads((output_dir / "dimensioned_array_candidates.json").read_text(encoding="utf-8"))
            self.assertTrue(
                any(
                    candidate["interpretation"] == "uint16"
                    and candidate["element_count"] == 900
                    and "30x30" in candidate["possible_dimensions"]
                    for candidate in dimensions["candidates"]
                )
            )
            cross_refs = json.loads(
                (output_dir / "cross_layer_index_reference_candidates.json").read_text(encoding="utf-8")
            )
            self.assertGreater(cross_refs["candidate_count"], 0)
            self.assertTrue(any("tracked_nodes" in candidate["set_hits"] for candidate in cross_refs["candidates"]))
            self.assertGreaterEqual(manifest["png_outputs"]["candidate_mask_count"], 1)

    def test_detects_coordinate_like_residual_without_approving_mutation(self) -> None:
        coordinates = [(0, 0), (12, 18), (64, 128), (100, 140), (256, 300), (320, 24)]
        residual = b"".join(struct.pack("<HH", x, y) for x, y in coordinates)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = write_source(root, residual)
            output_dir = root / "evidence"

            manifest = q2r.analyze_map_setting_unclassified_sections(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            coordinate = json.loads((output_dir / "coordinate_like_value_candidates.json").read_text(encoding="utf-8"))
            self.assertGreater(coordinate["candidate_count"], 0)
            self.assertEqual("candidate_not_proven", manifest["node_world_transform"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

    def test_rejects_output_inside_repository_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = write_source(root)
            output_dir = REPO_ROOT / "q2r_repo_output_should_not_exist"

            with self.assertRaises(SystemExit) as raised:
                q2r.analyze_map_setting_unclassified_sections(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("repository", str(raised.exception))
            self.assertEqual(synthetic_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2r"

            with self.assertRaises(SystemExit) as raised:
                q2r.analyze_map_setting_unclassified_sections(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = write_source(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "map_setting_section_inventory.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2r.analyze_map_setting_unclassified_sections(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
