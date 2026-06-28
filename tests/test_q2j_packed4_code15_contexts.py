from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import analyze_packed4_code15_contexts as q2j
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


def synthetic_code15_map_setting(logical_size: int = 4) -> bytes:
    matrix_size = logical_size * logical_size
    connected_code15_pairs = {(0, matrix_size - 1), (matrix_size - 1, 0)}
    blocked_code15_pairs = {(5, 10)}
    chunked: list[int] = []
    packed0: list[int] = []
    for source in range(matrix_size):
        sx = source % logical_size
        sy = source // logical_size
        for target in range(matrix_size):
            tx = target % logical_size
            ty = target // logical_size
            if source == target or (source, target) in blocked_code15_pairs:
                chunked.append(0)
                packed0.append(15)
                continue
            chunked.append(1)
            if (source, target) in connected_code15_pairs:
                packed0.append(15)
            else:
                packed0.append(CODE_BY_DELTA[(sign(tx - sx), sign(ty - sy))])
    packed1 = [0, 1, 2, 3]
    return pack_chunked_binary_matrix(chunked, logical_size=logical_size) + pack_packed4(packed0) + pack_packed4(packed1)


class Q2jPacked4Code15ContextTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_code15_map_setting())
        return source

    def test_analysis_writes_json_only_and_classifies_recoverable_code15(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            manifest = q2j.analyze_packed4_code15_contexts(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            expected_files = [
                "packed4_code15_contexts.json",
                "packed4_code15_distance_buckets.json",
                "packed4_code15_endpoint_classes.json",
                "packed4_code15_path_recovery.json",
                "q2j_code15_interpretation.json",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).is_file(), name)
            self.assertFalse((output_dir / "map_setting.q2j.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertEqual("likely_special_fallback_or_uncached_relation", manifest["code15_interpretation"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["third_chunked_binary_runtime_probe_allowed"])

            contexts = json.loads((output_dir / "packed4_code15_contexts.json").read_text(encoding="utf-8"))
            self.assertEqual(17, contexts["context_counts"]["packed4_0_eq_15_and_chunked_binary_eq_0"])
            self.assertEqual(2, contexts["context_counts"]["packed4_0_eq_15_and_chunked_binary_eq_1"])

            recovery = json.loads((output_dir / "packed4_code15_path_recovery.json").read_text(encoding="utf-8"))
            self.assertEqual(2, recovery["connected_nonself_code15_total"])
            self.assertEqual(1.0, recovery["recovery_ratios"]["any_without_15"])

            interpretation = json.loads((output_dir / "q2j_code15_interpretation.json").read_text(encoding="utf-8"))
            self.assertEqual("continue_static_decoding", interpretation["next_recommended_step"])
            self.assertFalse(interpretation["runtime_mutation_allowed"])
            self.assertFalse(interpretation["packed4_mutation_allowed"])

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2j"

            with self.assertRaises(SystemExit) as raised:
                q2j.analyze_packed4_code15_contexts(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_code15_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "packed4_code15_contexts.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2j.analyze_packed4_code15_contexts(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
