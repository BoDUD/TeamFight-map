from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import analyze_code15_component_graph as q2k
from tools import map_setting_round_trip
from test_map_setting_round_trip import pack_chunked_binary_matrix, pack_packed4


def synthetic_component_map_setting(logical_size: int = 4) -> bytes:
    matrix_size = logical_size * logical_size
    left_component = set(range(0, matrix_size // 2))
    right_component = set(range(matrix_size // 2, matrix_size))
    code15_pairs = {(1, 14), (14, 1), (2, 13), (13, 2)}
    chunked: list[int] = []
    packed0: list[int] = []
    for source in range(matrix_size):
        for target in range(matrix_size):
            same_side = (source in left_component and target in left_component) or (
                source in right_component and target in right_component
            )
            if source == target:
                chunked.append(0)
                packed0.append(15)
            elif (source, target) in code15_pairs:
                chunked.append(1)
                packed0.append(15)
            elif same_side:
                chunked.append(1)
                packed0.append(0)
            else:
                chunked.append(0)
                packed0.append(15)
    packed1 = [(node % 4) for node in range(matrix_size) for _slot in range(logical_size)]
    return pack_chunked_binary_matrix(chunked, logical_size=logical_size) + pack_packed4(packed0) + pack_packed4(packed1)


class Q2kCode15ComponentGraphTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_component_map_setting())
        return source

    def test_analysis_writes_json_only_and_detects_cross_component_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            manifest = q2k.analyze_code15_component_graph(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            expected_files = [
                "no15_component_summary.json",
                "code15_cross_component_edges.json",
                "code15_component_pair_matrix.json",
                "prior_probe_component_context.json",
                "packed4_1_component_correlation.json",
                "q2k_code15_component_interpretation.json",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2k.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertEqual("cross_component_bridge_candidate", manifest["code15_component_role"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

            summary = json.loads((output_dir / "no15_component_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(2, summary["component_count"])

            cross_edges = json.loads((output_dir / "code15_cross_component_edges.json").read_text(encoding="utf-8"))
            self.assertEqual(4, cross_edges["code15_connected_nonself_edge_count"])
            self.assertEqual(4, cross_edges["cross_component_count"])
            self.assertEqual(0, cross_edges["same_component_count"])
            self.assertEqual(1.0, cross_edges["cross_component_ratio"])

            packed1 = json.loads((output_dir / "packed4_1_component_correlation.json").read_text(encoding="utf-8"))
            self.assertIn("node_major_900x30", packed1["assumptions"])

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2k"

            with self.assertRaises(SystemExit) as raised:
                q2k.analyze_code15_component_graph(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_component_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "no15_component_summary.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2k.analyze_code15_component_graph(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
