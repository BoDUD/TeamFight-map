from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools import map_setting_round_trip as round_trip
from tools import map_setting_validate_semantics as semantics
from test_map_setting_round_trip import synthetic_map_setting


class MapSettingValidateSemanticsTests(unittest.TestCase):
    def test_chunked_invariants_detect_reachability_closure(self) -> None:
        values = [
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
        ]

        invariants = semantics.chunked_invariants(values, size=4)

        self.assertTrue(invariants["closure_like"])
        self.assertEqual(0, invariants["connected_pair_row_signature_mismatch_count"])
        self.assertEqual(0, invariants["transitivity_violation_count"])
        self.assertEqual(2, invariants["unique_row_count"])

    def test_chunked_invariants_detect_non_transitive_pairwise_relation(self) -> None:
        values = [
            1,
            1,
            0,
            1,
            1,
            1,
            0,
            1,
            1,
        ]

        invariants = semantics.chunked_invariants(values, size=3)

        self.assertFalse(invariants["closure_like"])
        self.assertGreater(invariants["connected_pair_row_signature_mismatch_count"], 0)
        self.assertGreater(invariants["transitivity_violation_count"], 0)

    def test_contingency_table_reports_sentinel_probabilities(self) -> None:
        contingency = semantics.contingency_table(
            chunked=[0, 0, 1, 1],
            packed=[15, 15, 2, 15],
        )

        self.assertEqual(
            1.0,
            contingency["probabilities"]["p_packed4_0_eq_15_given_chunked_binary_eq_0"],
        )
        self.assertEqual(
            0.666667,
            contingency["probabilities"]["p_chunked_binary_eq_0_given_packed4_0_eq_15"],
        )
        self.assertTrue(contingency["sentinel_hypothesis"]["chunked_0_strongly_implies_packed4_0_15"])
        self.assertFalse(contingency["sentinel_hypothesis"]["packed4_0_15_strongly_implies_chunked_0"])

    def test_adjacent_direction_distributions_resolve_stable_codes(self) -> None:
        logical_size = 3
        matrix_size = logical_size * logical_size
        packed = [15] * (matrix_size * matrix_size)
        direction_to_code = {
            (-1, -1): 0,
            (0, -1): 1,
            (1, -1): 2,
            (-1, 0): 3,
            (1, 0): 4,
            (-1, 1): 5,
            (0, 1): 6,
            (1, 1): 7,
        }
        for source_y in range(logical_size):
            for source_x in range(logical_size):
                source = source_y * logical_size + source_x
                for (dx, dy), code in direction_to_code.items():
                    target_x = source_x + dx
                    target_y = source_y + dy
                    if 0 <= target_x < logical_size and 0 <= target_y < logical_size:
                        target = target_y * logical_size + target_x
                        packed[source * matrix_size + target] = code

        mapping = semantics.adjacent_direction_distributions(packed, logical_size=logical_size)

        self.assertEqual("stable", mapping["stability"])
        self.assertEqual([], mapping["unresolved_codes"])
        self.assertEqual("N", mapping["code_to_direction"]["1"])
        self.assertEqual("E", mapping["code_to_direction"]["4"])

    def test_candidate_decision_rejects_closure_like_chunked_layer(self) -> None:
        decision = semantics.candidate_decision(
            invariants={"closure_like": True},
            candidate_cross_layer={
                "cross_layer_consistency_after_hypothetical_edit": "no_packed4_0_conflict_detected_for_this_edge"
            },
            direction_mapping={"stability": "stable"},
            scores={"conclusion": "single_best"},
        )

        self.assertEqual("rejected", decision["candidate_status"])
        self.assertFalse(decision["may_enter_mutation_pr"])
        self.assertIn("transitive reachability closure", decision["blockers"][0])

    def test_transform_unit_point_basic_orientations(self) -> None:
        self.assertEqual((0.25, 0.75), semantics.transform_unit_point(0.25, 0.75, "identity"))
        self.assertEqual((0.25, 0.25), semantics.transform_unit_point(0.25, 0.75, "rotate90"))
        self.assertEqual((0.75, 0.25), semantics.transform_unit_point(0.25, 0.75, "rotate180"))
        self.assertEqual((0.75, 0.75), semantics.transform_unit_point(0.25, 0.75, "rotate270"))

    def test_draw_runtime_grid_probe_writes_png(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "runtime_grid_probe.png"

            info = semantics.draw_runtime_grid_probe(output, "identity")

            self.assertTrue(output.exists())
            self.assertEqual([1280, 1280], info["size"])
            with Image.open(output) as image:
                self.assertEqual((1280, 1280), image.size)
                self.assertEqual("PNG", image.format)

    def test_semantic_tool_rejects_layout_hardlink_output_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source" / "map_setting"
            output_dir = root / "evidence"
            layout = root / "layout.json"
            hardlink = output_dir / "runtime_grid_probe.png"
            source.parent.mkdir()
            output_dir.mkdir()
            source.write_bytes(synthetic_map_setting())
            layout.write_bytes(b'{"layout":"protected"}')
            try:
                os.link(layout, hardlink)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")

            source_before = source.read_bytes()
            layout_before = layout.read_bytes()
            with self.assertRaises(SystemExit) as raised:
                semantics.ensure_no_output_conflicts(
                    input_path=source.resolve(),
                    output_dir=output_dir.resolve(),
                    layout_path=layout.resolve(),
                )

            self.assertIn("Refusing to overwrite layout", str(raised.exception))
            self.assertEqual(source_before, source.read_bytes())
            self.assertEqual(layout_before, layout.read_bytes())

    def test_semantic_tool_rejects_repository_internal_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(SystemExit) as raised:
                semantics.ensure_no_output_conflicts(
                    input_path=round_trip.REPO_ROOT / "README.md",
                    output_dir=Path(temp_dir) / "evidence",
                )

            self.assertIn("repository-internal input", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
