from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import analyze_packed4_next_hop_semantics as q2i
from tools import map_setting_round_trip
from test_map_setting_round_trip import pack_chunked_binary_matrix, pack_packed4


CODE_BY_DELTA = {
    (0, -1): 0,
    (1, -1): 1,
    (1, 0): 2,
    (1, 1): 3,
    (0, 1): 4,
    (-1, 1): 5,
    (-1, 0): 6,
    (-1, -1): 7,
}


def sign(value: int) -> int:
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def synthetic_next_hop_map_setting(logical_size: int = 4) -> bytes:
    matrix_size = logical_size * logical_size
    chunked: list[int] = []
    packed0: list[int] = []
    for source in range(matrix_size):
        sx = source % logical_size
        sy = source // logical_size
        for target in range(matrix_size):
            tx = target % logical_size
            ty = target // logical_size
            if source == target:
                chunked.append(0)
                packed0.append(15)
                continue
            chunked.append(1)
            packed0.append(CODE_BY_DELTA[(sign(tx - sx), sign(ty - sy))])
    packed1 = [0, 1, 2, 3]
    return pack_chunked_binary_matrix(chunked, logical_size=logical_size) + pack_packed4(packed0) + pack_packed4(packed1)


class Q2iPacked4NextHopSemanticsTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_next_hop_map_setting())
        return source

    def test_analysis_writes_json_only_and_detects_strong_next_hop_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            manifest = q2i.analyze_packed4_next_hop_semantics(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
                sample_limit=100,
            )

            expected_files = [
                "packed4_value_histogram.json",
                "packed4_direction_code_candidates.json",
                "packed4_path_follow_samples.json",
                "packed4_code15_analysis.json",
                "q2i_next_hop_interpretation.json",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2i.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertEqual("strong_next_hop_candidate", manifest["packed4_0_interpretation"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])

            interpretation = json.loads((output_dir / "q2i_next_hop_interpretation.json").read_text(encoding="utf-8"))
            self.assertEqual("strong_next_hop_candidate", interpretation["packed4_0_interpretation"])
            self.assertFalse(interpretation["runtime_mutation_allowed"])
            self.assertFalse(interpretation["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(interpretation["packed4_mutation_allowed"])

            path_samples = json.loads((output_dir / "packed4_path_follow_samples.json").read_text(encoding="utf-8"))
            self.assertEqual("strong_unverified", path_samples["next_hop_hypothesis"])
            self.assertEqual(1.0, path_samples["reached_ratio"])

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2i"

            with self.assertRaises(SystemExit) as raised:
                q2i.analyze_packed4_next_hop_semantics(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_next_hop_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "packed4_value_histogram.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2i.analyze_packed4_next_hop_semantics(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())

    def test_main_rejects_non_positive_sample_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = self.write_source(Path(temp_dir))
            with self.assertRaises(SystemExit) as raised:
                old_argv = [
                    "analyze_packed4_next_hop_semantics.py",
                    "--input",
                    str(source),
                    "--output-dir",
                    str(Path(temp_dir) / "evidence"),
                    "--expected-sha256",
                    map_setting_round_trip.sha256_file(source),
                    "--sample-limit",
                    "0",
                ]
                import sys

                previous = sys.argv
                try:
                    sys.argv = old_argv
                    q2i.main()
                finally:
                    sys.argv = previous

            self.assertIn("sample-limit", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
