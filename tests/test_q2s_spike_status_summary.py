from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import summarize_spike_status as q2s


REPO_ROOT = Path(__file__).resolve().parents[1]


class Q2sSpikeStatusSummaryTests(unittest.TestCase):
    def test_writes_status_matrix_without_runtime_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "evidence" / "q2s_status_matrix.json"

            summary = q2s.write_status_matrix(output)

            self.assertTrue(output.is_file())
            matrix = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("blocked_pending_runtime_anchor", matrix["q2_map_setting_route_status"])
            self.assertEqual("choose_visual_only_deliverable_or_runtime_anchor_spike", matrix["recommended_next_route"])
            self.assertEqual("route_a_visual_only_deliverable", matrix["next_pr_recommendation"]["preferred"])
            self.assertFalse(matrix["runtime_mutation_allowed"])
            self.assertFalse(matrix["packed4_mutation_allowed"])
            self.assertFalse(matrix["third_chunked_binary_runtime_probe_allowed"])
            self.assertFalse(matrix["map_editing_allowed"])
            self.assertFalse((output.parent / "map_setting.q2s.mutated.map_setting").exists())
            self.assertFalse((output.parent / "mod.override_info").exists())
            self.assertEqual(str(output.resolve()), summary["output"]["path"])

    def test_route_a_forbids_gameplay_data(self) -> None:
        matrix = q2s.build_status_matrix()

        route = matrix["route_a_visual_only_deliverable"]
        self.assertEqual("allowed_for_separate_pr", route["status"])
        self.assertIn("background_5v5", route["allowed"])
        self.assertIn("minimap_5v5_bg", route["allowed"])
        self.assertIn("map_setting", route["forbidden"])
        self.assertIn("collision/path/spawn data", route["forbidden"])
        self.assertIn("AI route edits", route["forbidden"])

    def test_route_b_requires_anchor_before_map_editing(self) -> None:
        matrix = q2s.build_status_matrix()

        route = matrix["route_b_runtime_anchor_spike"]
        self.assertEqual("allowed_for_separate_pr", route["status"])
        self.assertIn("node_world_transform", route["must_prove_before_map_editing"])
        self.assertIn("field semantic proof", route["must_prove_before_map_editing"])
        self.assertIn("one small local reversible effect", route["must_prove_before_map_editing"])
        self.assertIn("map_setting mutation", route["must_not_mix_with"])

    def test_rejects_repository_internal_output_without_writing(self) -> None:
        output = REPO_ROOT / "q2s_status_matrix_should_not_exist.json"

        with self.assertRaises(SystemExit) as raised:
            q2s.write_status_matrix(output)

        self.assertIn("repository-internal", str(raised.exception))
        self.assertFalse(output.exists())

    def test_rejects_output_under_runtime_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "game" / "mods" / "tfm2_lol_map_spike" / "q2s_status_matrix.json"

            with self.assertRaises(SystemExit) as raised:
                q2s.write_status_matrix(output)

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
