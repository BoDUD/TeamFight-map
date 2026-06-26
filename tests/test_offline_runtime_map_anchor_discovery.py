from __future__ import annotations

import json
import os
import struct
import tempfile
import unittest
from pathlib import Path

from tools import audit_bundle_map_assets, bundle_utils, derive_map_setting_path_graph, scan_setting_anchor_candidates


class OfflineRuntimeMapAnchorDiscoveryTests(unittest.TestCase):
    def make_bundle(self, path: Path) -> bytes:
        map_payload = bytearray()
        map_payload += struct.pack("<Q", 30)
        map_payload += struct.pack("<I", 900)
        map_payload += struct.pack("<ff", 12.5, 44.25)
        map_payload += struct.pack("<hh", 320, 640)
        bundle_utils.write_synthetic_bundle(
            path,
            [
                ("bytes", "asset/base/setting/map_setting", bytes(map_payload)),
                ("png", "asset/base/aseprite_resources/ingame/5v5/wall_5v5", b"\x89PNG\r\n\x1a\nfake"),
                ("txt", "asset/base/champion/not_map", b"ignored"),
            ],
        )
        return bytes(map_payload)

    def test_audit_bundle_writes_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "bundle.game_data"
            self.make_bundle(bundle)
            output_dir = root / "evidence"

            manifest = audit_bundle_map_assets.audit_bundle(bundle, output_dir)

            self.assertFalse(manifest["payloads_written"])
            self.assertTrue((output_dir / "bundle_asset_index.json").is_file())
            self.assertTrue((output_dir / "bundle_map_related_assets.json").is_file())
            self.assertTrue((output_dir / "bundle_map_anchor_candidates.json").is_file())
            self.assertIn(
                "asset/base/setting/map_setting",
                {candidate["asset_key"] for candidate in manifest["candidates"]},
            )
            related = json.loads((output_dir / "bundle_map_related_assets.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(related["related_asset_count"], 2)
            self.assertFalse(related["payloads_written"])
            self.assertNotIn("ignored", json.dumps(related).lower())

    def test_audit_bundle_rejects_output_hardlink_alias_of_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "bundle.game_data"
            self.make_bundle(bundle)
            output_dir = root / "evidence"
            output_dir.mkdir()
            alias = output_dir / "bundle_asset_index.json"
            try:
                os.link(bundle, alias)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = bundle.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                audit_bundle_map_assets.audit_bundle(bundle, output_dir)

            self.assertIn("Refusing to overwrite bundle", str(raised.exception))
            self.assertEqual(before, bundle.read_bytes())

    def test_scan_setting_candidates_reports_unverified_tables_without_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "bundle.game_data"
            self.make_bundle(bundle)
            output_dir = root / "evidence"
            audit_bundle_map_assets.audit_bundle(bundle, output_dir)

            report = scan_setting_anchor_candidates.scan_candidates(
                bundle,
                output_dir / "bundle_map_related_assets.json",
                output_dir,
            )

            self.assertEqual("no_sufficient_anchor_found", report["offline_anchor_result"])
            self.assertEqual("unproven", report["map_setting_node_world_transform"])
            self.assertEqual("blocked", report["candidate_369_370"])
            self.assertGreaterEqual(report["unverified_coordinate_table_count"], 1)
            tables = json.loads((output_dir / "possible_coordinate_tables.json").read_text(encoding="utf-8"))
            self.assertFalse(tables["coordinate_tables_confirmed"])
            self.assertFalse(tables["payloads_written"])

    def test_scan_setting_candidates_rejects_output_alias_of_asset_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "bundle.game_data"
            self.make_bundle(bundle)
            output_dir = root / "evidence"
            output_dir.mkdir()
            asset_index = root / "asset_index.json"
            asset_index.write_text(json.dumps({"assets": []}), encoding="utf-8")
            alias = output_dir / "anchor_candidate_report.json"
            try:
                os.link(asset_index, alias)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = asset_index.read_text(encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                scan_setting_anchor_candidates.scan_candidates(bundle, asset_index, output_dir)

            self.assertIn("Refusing to overwrite asset index", str(raised.exception))
            self.assertEqual(before, asset_index.read_text(encoding="utf-8"))

    def test_path_follow_reaches_target_on_synthetic_next_hop(self) -> None:
        logical_size = 3
        matrix_size = logical_size * logical_size
        packed = [15] * (matrix_size * matrix_size)
        code_to_delta = {4: (1, 0)}
        packed[0 * matrix_size + 2] = 4
        packed[1 * matrix_size + 2] = 4

        result = derive_map_setting_path_graph.follow_path(
            packed,
            source=0,
            target=2,
            code_to_delta=code_to_delta,
            logical_size=logical_size,
        )

        self.assertEqual("reached", result["status"])
        self.assertEqual(2, result["steps"])

    def test_derive_local_adjacency_records_direction_consistency(self) -> None:
        logical_size = 3
        matrix_size = logical_size * logical_size
        chunked = [0] * (matrix_size * matrix_size)
        packed = [15] * (matrix_size * matrix_size)
        source = 0
        target = 1
        chunked[source * matrix_size + target] = 1
        chunked[target * matrix_size + source] = 1
        packed[source * matrix_size + target] = 4
        packed[target * matrix_size + source] = 3

        adjacency = derive_map_setting_path_graph.derive_local_adjacency(
            chunked,
            packed,
            code_to_delta={4: (1, 0), 3: (-1, 0)},
            logical_size=logical_size,
        )

        first_edge = next(edge for edge in adjacency["edges"] if edge["source"] == source and edge["target"] == target)
        self.assertTrue(first_edge["open"])
        self.assertTrue(first_edge["forward_code_matches_neighbor_delta"])
        self.assertTrue(first_edge["reverse_code_matches_neighbor_delta"])
        self.assertEqual(1, adjacency["direction_consistency_counts"]["both_consistent"])


if __name__ == "__main__":
    unittest.main()
