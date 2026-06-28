from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import analyze_chunked_binary_probe_targets as q2h
from tools import map_setting_round_trip
from test_map_setting_round_trip import synthetic_map_setting


class Q2hChunkedBinaryProbeSynthesisTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_map_setting())
        return source

    def test_classify_sum_marks_sparse_and_universal_like(self) -> None:
        self.assertEqual("zero", q2h.classify_sum(0, 900))
        self.assertEqual("sparse", q2h.classify_sum(27, 900))
        self.assertEqual("middle", q2h.classify_sum(450, 900))
        self.assertEqual("near_universal", q2h.classify_sum(899, 900))
        self.assertEqual("universal_like", q2h.classify_sum(900, 900))

    def test_analysis_writes_json_only_and_blocks_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            manifest = q2h.analyze_chunked_binary_probe_targets(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
            )

            row_classes = output_dir / "chunked_binary_row_column_classes.json"
            prior_analysis = output_dir / "prior_probe_target_analysis.json"
            next_strategy = output_dir / "next_candidate_strategy.json"
            self.assertTrue(row_classes.is_file())
            self.assertTrue(prior_analysis.is_file())
            self.assertTrue(next_strategy.is_file())
            self.assertFalse((output_dir / "map_setting.q2h.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertTrue(manifest["safety"]["read_only"])
            self.assertFalse(manifest["safety"]["mutated_map_setting_generated"])
            self.assertFalse(manifest["safety"]["runtime_install_modified"])
            self.assertEqual("continue_static_decoding", manifest["next_action"])
            self.assertTrue(manifest["do_not_run_third_runtime_probe_now"])

            strategy = json.loads(next_strategy.read_text(encoding="utf-8"))
            self.assertEqual("q2h_next_candidate_strategy", strategy["probe"])
            self.assertEqual("continue_static_decoding", strategy["next_action"])
            self.assertTrue(strategy["third_candidate_requires_separate_risk_review"])
            self.assertIn("no packed4 mutation", strategy["if_a_future_third_candidate_is_reviewed"]["constraints"])

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2h"

            with self.assertRaises(SystemExit) as raised:
                q2h.analyze_chunked_binary_probe_targets(
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
            source = self.write_source(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "chunked_binary_row_column_classes.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2h.analyze_chunked_binary_probe_targets(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
