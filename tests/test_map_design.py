from __future__ import annotations

import unittest

from tools.validate_map_design import load_layout, validate_layout


class MapDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = load_layout()

    def test_layout_satisfies_design_constraints(self) -> None:
        self.assertEqual([], validate_layout(self.layout))

    def test_mvp_region_codes_are_present(self) -> None:
        expected = {
            "LANE_TOP",
            "LANE_MID",
            "LANE_BOTTOM",
            "RIVER_TOP",
            "RIVER_BOTTOM",
            "PIT_MORGARD",
            "PIT_SERPEN",
            "JUNGLE_BLUE_TOP",
            "JUNGLE_BLUE_BOT",
            "JUNGLE_RED_TOP",
            "JUNGLE_RED_BOT",
            "BASE_BLUE",
            "BASE_RED"
        }
        self.assertTrue(expected.issubset(set(self.layout["region_codes"])))

    def test_objective_roles_match_design_book(self) -> None:
        roles = {objective["id"]: objective["objective_role"] for objective in self.layout["objectives"]}
        self.assertEqual("timed_push_pressure", roles["PIT_MORGARD"])
        self.assertEqual("permanent_growth", roles["PIT_SERPEN"])

    def test_objective_pits_use_two_explicit_gate_nodes(self) -> None:
        edges = {tuple(edge) for edge in self.layout["topology"]["edges"]}
        for objective in self.layout["objectives"]:
            gate_ids = {entrance["gate_id"] for entrance in objective["entrances"]}
            self.assertEqual(2, len(gate_ids))
            for gate_id in gate_ids:
                self.assertIn((gate_id, objective["id"]), edges)

    def test_jungle_mid_relationship_is_adjacency_not_exit(self) -> None:
        for half in self.layout["jungle"]["half_jungles"]:
            self.assertIn("LANE_MID", half["adjacent_regions"])
            self.assertNotIn("LANE_MID", {exit_info["to"] for exit_info in half["exits"]})


if __name__ == "__main__":
    unittest.main()
