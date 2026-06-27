from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import map_setting_round_trip
from tools import select_q2f_semantic_probe_candidates as q2f
from test_map_setting_round_trip import synthetic_map_setting


class Q2fSemanticProbeCandidateTests(unittest.TestCase):
    def write_source(self, root: Path) -> Path:
        source = root / "source" / "map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(synthetic_map_setting())
        return source

    def test_candidate_plan_writes_json_only_and_keeps_runtime_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"

            manifest = q2f.build_q2f_candidate_plan(
                input_path=source,
                output_dir=output_dir,
                expected_sha256=map_setting_round_trip.sha256_file(source),
                top_n=3,
            )

            candidates_path = output_dir / "q2f_semantic_probe_candidates.json"
            decision_path = output_dir / "q2f_candidate_decision.json"
            self.assertTrue(candidates_path.is_file())
            self.assertTrue(decision_path.is_file())
            self.assertFalse((output_dir / "map_setting.q2f.mutated.map_setting").exists())
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertTrue(manifest["safety"]["read_only"])
            self.assertFalse(manifest["safety"]["mutated_map_setting_generated"])
            self.assertFalse(manifest["safety"]["runtime_install_modified"])
            self.assertEqual(
                "A_repeat_q2e_369_370_extended_observation",
                manifest["decision"]["q2f_recommended_next_runtime_option"],
            )
            self.assertFalse(manifest["decision"]["second_candidate_may_enter_runtime_probe"])
            candidates = manifest["selection"]["candidates"]
            self.assertGreaterEqual(len(candidates), 1)
            self.assertLessEqual(len(candidates), 3)
            for candidate in candidates:
                self.assertEqual("chunked_binary", candidate["layer"])
                self.assertEqual(2, candidate["changed_cell_count"])
                self.assertEqual(2, candidate["changed_byte_count"])
                self.assertEqual([1, 1], candidate["old_values"])
                self.assertEqual([0, 0], candidate["planned_new_values"])
                self.assertFalse(candidate["may_enter_runtime_probe"])
                self.assertFalse(candidate["mutation_generated"])
                self.assertNotEqual(candidate["edge"][0], candidate["edge"][1])

            written = json.loads(candidates_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["input_sha256"], written["input_sha256"])

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "q2f"

            with self.assertRaises(SystemExit) as raised:
                q2f.build_q2f_candidate_plan(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertEqual(synthetic_map_setting(), source.read_bytes())
            self.assertFalse(output_dir.exists())

    def test_rejects_candidate_output_hardlink_alias_to_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self.write_source(root)
            output_dir = root / "evidence"
            output_dir.mkdir()
            hardlink = output_dir / "q2f_semantic_probe_candidates.json"
            try:
                os.link(source, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                q2f.build_q2f_candidate_plan(
                    input_path=source,
                    output_dir=output_dir,
                    expected_sha256=map_setting_round_trip.sha256_file(source),
                )

            self.assertIn("Refusing to overwrite input", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
